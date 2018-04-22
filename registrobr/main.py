import requests
import bs4
import re
from collections import namedtuple

_A_RECORD = namedtuple('A_RECORD', ['ownername', 'ip'])
_AAAA_RECORD = namedtuple('AAAA_RECORD', ['ownername', 'ipv6'])
_CNAME_RECORD = namedtuple('CNAME_RECORD', ['ownername', 'server'])
_TXT_RECORD = namedtuple('TXT_RECORD', ['ownername', 'data'])
_MX_RECORD = namedtuple('MX_RECORD', ['ownername', 'priority', 'email_server'])
_TLSA_RECORD = namedtuple('TLSA_RECORD', ['ownername', 'usage', 'selector', 'matching', 'data'])

class RegistroBrAPI:
    def __init__(self, user, password, otp=None):
        self._session = requests.session()
        self._user, self._password, self._otp = user, password, otp

    def login(self):
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

    def domains(self):
        url = f'https://registro.br/cgi-bin/nicbr/user_domains?request_token={self._request_token}'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies
        DomainT = namedtuple('Domain', ['Id', 'FQDN', 'ExpirationDate', 'Status', 'Contact', 'PayLink', 'Auctionable'])
        domains = [DomainT(**d) for d in r.json()['domains']]
        return domains

    def zone_info(self, domain):
        url = f'https://registro.br/2/freedns?fqdn={domain.FQDN}&request_token={self._request_token}'
        r = self._session.get(url, cookies=self._cookies,
                              headers=self._headers)
        self._cookies = r.cookies
        bs = bs4.BeautifulSoup(r.content, "lxml")
        records = bs.findAll('input', id=re.compile('^rr-[0-9]+'))
        parsed_records = self.__parse_records(domain, records)
        return parsed_records
        # print(f'{" Zone info ":=^80}')
        # for record in parsed_records:
        #     print(record)

    def __parse_records(self, domain, records):
        parsed_records = []
        for record in records:
            ownername, type, data = record["value"].split('|')

            _tuple = namedtuple(f'{type}_RECORD', ['ownername', 'data'])(
                ownername, data)

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
        url = f'https://registro.br/2/freedns?fqdn={domain.FQDN}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'add-rr-'+str(count): record})
        self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)

    def remove_records(self, domain, records):
        url = f'https://registro.br/2/freedns?fqdn={domain.FQDN}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'remove-rr-'+str(count): record})
        self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)

    @staticmethod
    def create_a_record(ownername, ip):
        return _A_RECORD(ownername, ip)

    @staticmethod
    def create_aaaa_record(ownername, ipv6):
        return _AAAA_RECORD(ownername, ipv6)

    @staticmethod
    def create_cname_record(ownername, server):
        return _CNAME_RECORD(ownername, server)

    @staticmethod
    def create_mx_record(ownername, priority, email_server):
        return _MX_RECORD(ownername, priority, email_server)

    @staticmethod
    def create_txt_record(ownername, data):
        return _TXT_RECORD(ownername, data)

    @staticmethod
    def create_tlsa_record(ownername, usage, selector, matching, data):
        return _TLSA_RECORD(ownername, usage, selector, matching, data)
