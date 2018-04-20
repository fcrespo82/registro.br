#!/usr/bin/env python3

import requests
import re
import bs4
import argparse
import getpass
from collections import namedtuple


def config_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument('user')
    parser.add_argument('-p', '--password')
    parser.add_argument('-o', '--otp')
    commands = parser.add_subparsers(title='Commands', dest='command')
    commands.required = True

    domains_parser = commands.add_parser(
        'domains', help='List domains for this user')

    # zone_info_parser = commands.add_parser(
    # 'zone_info', help='List Zone Info for the domain')

    return parser


class RegistroBr:
    def __init__(self, user, password):
        self._session = requests.session()
        self._user, self._password = user, password

    def login(self, otp=None):
        url = 'https://registro.br/2/login'

        r = self._session.get(url)

        bs = bs4.BeautifulSoup(r.content, "lxml")
        request_token = bs.find(attrs={'id': 'request-token'})['value']

        self._headers = {
            'Request-Token': request_token
        }

        dados = {'user': self._user, 'password': self._password}

        url = 'https://registro.br/ajax/login'
        r = self._session.post(url, json=dados, headers=self._headers)
        self._cookies = r.cookies

        if not r.json()['success']:
            print(f'Falha ao logar: {r.json()["msg"]}')
            exit(1)

        if r.json()['otp']:
            if not otp:
                otp = input('OTP: ')
            url = 'https://registro.br/ajax/token'
            dados = {'otp': otp}
            r = self._session.post(
                url, json=dados, cookies=self._cookies, headers=self._headers)
            self._cookies = r.cookies

            if not r.json()['success']:
                print(f'Falha ao logar (OTP): {r.json()["msg"]}')
                exit(2)

        url = 'https://registro.br/2/painel'

        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies

        bs = bs4.BeautifulSoup(r.content, "lxml")
        self._request_token = bs.find(
            'input', attrs={'id': 'request_token'})['value']

    def domains(self):
        url = f'https://registro.br/cgi-bin/nicbr/user_domains?request_token={self._request_token}'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies
        return r.json()['domains']

    def zone_info(self, domain):
        print(
            f'Domínio {domain["FQDN"]} com status {domain["Status"]} expira em: {domain["ExpirationDate"]}')

        url = f'https://registro.br/2/freedns?fqdn={domain["FQDN"]}&request_token={self._request_token}'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies
        bs = bs4.BeautifulSoup(r.content, "lxml")
        records = bs.findAll('input', id=re.compile('^rr-[0-9]+'))
        parsed_records = self.__parse_records(domain, records)
        for record in parsed_records:
            print(record)

    def __parse_records(self, domain, records):
        parsed_records = []
        for record in records:
            name, type, data = record["value"].split('|')

            _tuple = namedtuple(f'{type}_RECORD', ['ownername', 'data'])(
                name, data)

            if type == 'TLSA':
                data = self.__parse_tlsa(data)
                _tuple = namedtuple(f'{type}_RECORD', ['ownername', 'usage', 'selector', 'matching', 'data'])(
                    name, *data)
            elif type == 'MX':
                data = self.__parse_mx(data)
                _tuple = namedtuple(f'{type}_RECORD', ['ownername', 'priority', 'email_server'])(
                    name, *data)

            parsed_records.append(_tuple)

        return parsed_records

    def __parse_tlsa(self, data):
        usage, selector, matching, data = data.rstrip().split(' ')
        usage_type = {0: 'CA', 1: 'Service certificate',
                      2: 'Trust Anchor', 3: 'Domain-issued certificate'}
        selector_type = {0: 'Subject Public Key', 1: 'Subject Public Key'}
        matching_type = {1: 'SHA-256', 2: 'SHA-512'}

        usage = (int(usage), usage_type[int(usage)])
        selector = (int(selector), selector_type[int(selector)])
        matching = (int(matching), matching_type[int(matching)])

        return usage, selector, matching, data

    def __parse_mx(self, data):
        priority, email_server = data.rstrip().split(' ')
        return (int(priority), email_server)

    def logout(self):
        url = 'https://registro.br/cgi-bin/nicbr/logout'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies

    def add_records(self, domain, records):
        url = f'https://registro.br/2/freedns?fqdn={domain["FQDN"]}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'add-rr-'+str(count): record})
        self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)

    def remove_records(self, domain, records):
        url = f'https://registro.br/2/freedns?fqdn={domain["FQDN"]}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'remove-rr-'+str(count): record})
        self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)

    def create_a_record(self, ownername, ip):
        return f'{ownername}|A|{ip}'

    def create_aaaa_record(self, ownername, ipv6):
        return f'{ownername}|AAAA|{ipv6}'

    def create_cname_record(self, ownername, server):
        return f'{ownername}|CNAME|{server}'

    def create_mx_record(self, ownername, priority, email_server):
        return f'{ownername}|MX|{priority} {email_server}'

    def create_txt_record(self, ownername, data):
        return f'{ownername}|TXT|{data}'

    def create_tlsa_record(self, ownername, usage, selector, matching, data):
        return f'{ownername}|TLSA|{usage} {selector} {matching} {data}'


def main():
    ARGS = config_argparse().parse_args()

    if not ARGS.password:
        ARGS.password = getpass.getpass()

    registrobr = RegistroBr(ARGS.user, ARGS.password)

    if ARGS.otp:
        registrobr.login(ARGS.otp)
    else:
        registrobr.login()

    if ARGS.command == 'domains':
        domains = registrobr.domains()

        for domain in domains:
            print(
                f'Domínio {domain["FQDN"]} com status {domain["Status"]} expira em: {domain["ExpirationDate"]}')

    # registrobr.zone_info(domains[0])

    # txt=registrobr.create_txt_record('owner', 'qualquer texto')

    # registrobr.add_records(domains[0], [txt])

    # registrobr.zone_info(domains[0])

    registrobr.logout()


if __name__ == '__main__':
    main()
