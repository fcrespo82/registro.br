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
    is_logged = False
    _cookies = None
    _headers = None
    def __init__(self, user, password=None, otp=None):
        self._session = requests.session()
        self._user, self._password, self._otp = user, password, otp
        self.is_logged = False

    def login(self):
        'Log in to registro.br'
        url = 'https://registro.br/v2/ajax/user/login'

        r = self._session.get(url)
        self._cookies = r.cookies

        bs = bs4.BeautifulSoup(r.content, "html5lib")
        # request_token = bs.find(attrs={'id': 'request-token'})['value']

        self._headers = {
            'X-XSRF-TOKEN': r.cookies.get('XSRF-TOKEN')
        }

        if not self._password:
            self._password = getpass('Password: ')

        dados = {'user': self._user, 'password': self._password}

        url = 'https://registro.br/v2/ajax/user/login'
        r = self._session.post(url, json=dados, cookies=self._cookies, headers=self._headers)
        self._cookies = r.cookies

        if not r.ok:
            print(f'Falha ao logar: {r.json()["msg"]}')
            exit(1)

        if 'otp' in r.json():
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

        bs = bs4.BeautifulSoup(r.content, "html5lib")
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
        bs = bs4.BeautifulSoup(r.content, "html5lib")
        records = bs.findAll('input', id=re.compile('^rr-[0-9]+'))
        parsed_records = self.__parse_records(domain, records)
        return parsed_records

    def __check_record(self, domain, record):
        items = [x for x in self.domains() if x.FQDN == domain]
        errors = False
        for item in items:
            records = self.zone_info(item)
            for rec in records:
                if type(rec) == type(record) and rec.ownername == record.ownername:
                    print("A " + type(record).__name__ + " for ownername " + record.ownername + " already exists")
                    errors = True
        if errors:
            exit(3)

        
    def __parse_records(self, domain, records):
        parsed_records = []
        for record in records:
            ownername, type, data = record["value"].split('|')

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

        usage = int(usage) #(int(usage), _TLSA_RECORD_USAGE[int(usage)])
        selector = int(selector) #(int(selector), _TLSA_RECORD_SELECTOR[int(selector)])
        matching = int(matching) #(int(matching), _TLSA_RECORD_MATCHING[int(matching)])

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
            self.is_logged = False

    def add_records(self, domain, records):
        'Add records to the domain'
        url = f'https://registro.br/2/freedns?fqdn={domain}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            self.__check_record(domain, record)
            dados.update({'add-rr-'+str(count): record})
            count = count + 1
        r = self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)
        if re.match("Erro ao adicionar o record", r.content):
            raise RuntimeError("Erro ao adicionar o record")
        return r

    def remove_records(self, domain, records):
        'Remove records from the domain'
        url = f'https://registro.br/2/freedns?fqdn={domain}'
        count = 0
        dados = {'request-token': self._request_token}
        for record in records:
            dados.update({'remove-rr-'+str(count): record})
            count = count + 1
        r = self._session.post(
            url, data=dados, cookies=self._cookies, headers=self._headers)
        return r

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
