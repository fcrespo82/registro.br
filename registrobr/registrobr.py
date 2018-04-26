import requests
import bs4
import re
from getpass import getpass
from ipaddress import IPv4Address, IPv6Address, AddressValueError
from collections import namedtuple
from abc import ABC

_A_RECORD = namedtuple('A_RECORD', ['ownername', 'ip'])
_AAAA_RECORD = namedtuple('AAAA_RECORD', ['ownername', 'ipv6'])
_CNAME_RECORD = namedtuple('CNAME_RECORD', ['ownername', 'server'])
_TXT_RECORD = namedtuple('TXT_RECORD', ['ownername', 'data'])
_MX_RECORD = namedtuple('MX_RECORD', ['ownername', 'priority', 'email_server'])
_TLSA_RECORD = namedtuple(
    'TLSA_RECORD', ['ownername', 'usage', 'selector', 'matching', 'data'])

_DOMAIN = namedtuple('Domain', [
                     'Id', 'FQDN', 'ExpirationDate', 'Status', 'Contact', 'PayLink', 'Auctionable'])

_TLSA_RECORD_USAGE = {0: 'CA', 1: 'Service certificate',
                      2: 'Trust Anchor', 3: 'Dom-issued certificate'}
_TLSA_RECORD_SELECTOR = {0: 'Subject Public Key', 1: 'Subject Public Key'}
_TLSA_RECORD_MATCHING = {1: 'SHA-256', 2: 'SHA-512'}


class RegistroBrAPI:
    def __init__(self, user, password=None, otp=None):
        self._session = requests.session()
        self._user, self._password, self._otp = user, password, otp
        self.is_logged = False

    def login(self):
        'Log in to registro.br'
        url = 'https://registro.br/2/login'

        r = self._session.get(url)

        bs = bs4.BeautifulSoup(r.content, "lxml")
        request_token = bs.find(attrs={'id': 'request-token'})['value']

        self._headers = {
            'Request-Token': request_token
        }

        if not self._password:
            self._password = getpass('Password: ')

        dados = {'user': self._user, 'password': self._password}

        url = 'https://registro.br/ajax/login'
        r = self._session.post(url, json=dados, headers=self._headers)
        self._cookies = r.cookies

        if not r.json()['success']:
            print(f'Falha ao logar: {r.json()["msg"]}')
            exit(1)

        if r.json()['otp']:
            if not self._otp:
                self._otp = input('OTP: ')
            url = 'https://registro.br/ajax/token'
            dados = {'otp': self._otp}
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
        self.is_logged = True

    def domains(self):
        'Domains from the user account'
        url = f'https://registro.br/cgi-bin/nicbr/user_domains?request_token={self._request_token}'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies
        domains = [_DOMAIN(**d) for d in r.json()['domains']]
        return domains

    def zone_info(self, domain):
        'Records from the domain'
        url = f'https://registro.br/2/freedns?fqdn={domain.FQDN}&request_token={self._request_token}'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies
        bs = bs4.BeautifulSoup(r.content, "lxml")
        records = bs.findAll('input', id=re.compile('^rr-[0-9]+'))
        parsed_records = self.__parse_records(domain, records)
        return {domain.FQDN: parsed_records}

    def __parse_records(self, domain, records):
        parsed_records = []
        for record in records:
            ownername, type, data = record["value"].split('|')

            # _tuple = namedtuple(f'{type}_RECORD', ['ownername', 'data'])(
            #     ownername, data)

            if type == 'A':
                _tuple = _A_RECORD(ownername, data)
            elif type == 'AAAA':
                _tuple = _AAAA_RECORD(ownername, data)
            elif type == 'CNAME':
                _tuple = _CNAME_RECORD(ownername, data)
            elif type == 'TLSA':
                data = self.__parse_tlsa(data)
                _tuple = _TLSA_RECORD(ownername, *data)
            elif type == 'MX':
                data = self.__parse_mx(data)
                _tuple = _MX_RECORD(ownername, *data)
            elif type == 'TXT':
                _tuple = _TXT_RECORD(ownername, data)

            parsed_records.append(_tuple)

        return parsed_records

    def __parse_tlsa(self, data):
        usage, selector, matching, data = data.rstrip().split(' ')

        usage = (int(usage), _TLSA_RECORD_USAGE[int(usage)])
        selector = (int(selector), _TLSA_RECORD_SELECTOR[int(selector)])
        matching = (int(matching), _TLSA_RECORD_MATCHING[int(matching)])

        return usage, selector, matching, data

    def __parse_mx(self, data):
        priority, email_server = data.rstrip().split(' ')
        return (int(priority), email_server)

    def logout(self):
        'Log out of registro.br'
        if self.is_logged:
            url = 'https://registro.br/cgi-bin/nicbr/logout'
            r = self._session.get(url, cookies=self._cookies,
                                  headers=self._headers)
            self._cookies = r.cookies

    def add_records(self, domain, records):
        'Add records to the domain'
        url = f'https://registro.br/2/freedns?fqdn={domain}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'add-rr-'+str(count): record})
        self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)

    def remove_records(self, domain, records):
        'Remove records from the domain'
        url = f'https://registro.br/2/freedns?fqdn={domain}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'remove-rr-'+str(count): record})
        self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)


def create_a_record(ownername, ip):
    'Creates an A record'
    try:
        IPv4Address(ip)
    except AddressValueError as addressValueError:
        raise ValueError(f'Invalid IP address: {addressValueError}')
    return _A_RECORD(ownername, ip)


def create_aaaa_record(ownername, ipv6):
    'Creates an AAAA record'
    try:
        IPv6Address(ipv6)
    except AddressValueError as addressValueError:
        raise ValueError(f'Invalid IP address: {addressValueError}')
    return _AAAA_RECORD(ownername, ipv6)


def create_cname_record(ownername, server):
    'Creates a CNAME record'
    return _CNAME_RECORD(ownername, server)


def create_mx_record(ownername, priority, email_server):
    'Creates a MX record'
    max_range = 65535
    if priority not in range(1, max_range):
        raise ValueError(f'Priority must be within 1-{max_range} range')
    return _MX_RECORD(ownername, priority, email_server)


def create_txt_record(ownername, data):
    'Creates a TXT record'
    return _TXT_RECORD(ownername, data)


def create_tlsa_record(ownername, usage, selector, matching, data):
    'Creates a TLS record'
    if usage not in _TLSA_RECORD_USAGE:
        raise ValueError(f'Usage must be one of {_TLSA_RECORD_USAGE}')
    if selector not in _TLSA_RECORD_SELECTOR:
        raise ValueError(f'Selector must be one of {_TLSA_RECORD_SELECTOR}')
    if matching not in _TLSA_RECORD_MATCHING:
        raise ValueError(f'Matching must be one of {_TLSA_RECORD_MATCHING}')
    return _TLSA_RECORD(ownername, usage, selector, matching, data)
