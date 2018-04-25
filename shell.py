#!/usr/bin/env python3
import cmd
from registrobr import RegistroBrAPI
from getpass import getpass
from collections import namedtuple

class RecordState:
    def __init__(self, state, record):
        self.State = state
        self.Record = record
    def __str__(self):
        return f'RecordState(State={self.State}, Record={self.Record})'

class RegistroBrShell(cmd.Cmd):
    intro = 'Welcome to the registro.br shell. Type help or ? to list commands.\n'
    prompt = '(registro.br) '
    _registrobr = None
    _records = dict()

    def do_mock(self, args):
        DomainT = namedtuple('Domain', ['Id', 'FQDN', 'ExpirationDate', 'Status', 'Contact', 'PayLink', 'Auctionable'])

        domain = DomainT(1, 'crespo.com.br', 'expiry', 'status', 'contact', 'paylink', False)
        self._domains = [domain]

        A_RECORD = namedtuple('A_RECORD', ['ownername', 'ip'])
        AAAA_RECORD = namedtuple('AAAA_RECORD', ['ownername', 'ipv6'])
        CNAME_RECORD = namedtuple('CNAME_RECORD', ['ownername', 'server'])
        TXT_RECORD = namedtuple('TXT_RECORD', ['ownername', 'data'])
        MX_RECORD = namedtuple('MX_RECORD', ['ownername', 'priority', 'email_server'])
        TLSA_RECORD = namedtuple('TLSA_RECORD', ['ownername', 'usage', 'selector', 'matching', 'data'])
        records = [
            # TXT_RECORD(ownername='_acme-challenge', data='"LupjAATGvUdOtoofGU4j_TK4WsZM5omLSuc5txLndfg"'), 
            # TLSA_RECORD(ownername='_test', usage=(0, 'CA'), selector=(1, 'Subject Public Key'), matching=(1, 'SHA-256'), data='d2abde240d7cd3ee6b4b28c54df034b9'), MX_RECORD(ownername='_test_mx', priority=10, email_server='test.mx.record'), CNAME_RECORD(ownername='fernando', server='fcrespo82.github.io'), CNAME_RECORD(ownername='blog.fernando', server='fcrespo82.github.io'), CNAME_RECORD(ownername='curriculo.fernando', server='fcrespo82.github.io'), CNAME_RECORD(ownername='nas', server='fcrespo82.myds.me'), TXT_RECORD(ownername='_dnsauth.nas', data='"201803271600392msn9aiznnhm90owmz8d5nc5nddaroa8gv5w7ca7czm2dxcm4c"'), 
            RecordState('Default', TXT_RECORD(ownername='owner', data='"qualquer texto"'))]

        self._records.update({domain.FQDN: records})

    def do_login(self, _):
        'Login to registro.br'
        user = input('user: ')
        password = getpass('password: ')
        opt = input('otp: ')
        self._registrobr = RegistroBrAPI(user, password, opt)
        self._registrobr.login()
        print('Logged in')


    def do_domains(self, _):
        'List domains registered to this account'
        if not self._domains:
            self._domains = self._registrobr.domains()
        for domain in self._domains:
            print(f'{domain.FQDN}')
    
    def do_zone_info(self, domain):
        'List records associated to this domain'
        if not domain:
            print('Please pass a domain as parameter')
            return
        'List zone info associated to this domain'
        if not self._domains:
            self._domains = self._registrobr.domains()
        filtered = filter(lambda d: d.FQDN == domain, self._domains)
        for domain in filtered:
            if not self._records:
                self._records = self._registrobr.zone_info(domain)
            print(*self._records[domain.FQDN], sep='\n')

    def domains_completion(self, text):
        if not self._domains:
            self._domains = self._registrobr.domains()
        filtered = filter(lambda d: d.FQDN.startswith(text), self._domains)
        mapped = [d.FQDN for d in filtered]
        return mapped

    def complete_zone_info(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_records(self, domain):
        'List records from a domain or all domains'
        if domain:
            filtered = [d for d in self._records if d == domain]
        else:
            filtered = self._records
        
        for domain_key in filtered:
            domain_key_spaced = f' {domain_key} '
            print(f'{domain_key_spaced:=^80}')
            for recordState in self._records[domain_key]:
                print(recordState) #.Record, recordState.State, sep=' - ')
            print(80*'=')

    def complete_records(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_txt_record(self, domain):
        if not domain:
            print('Please pass a domain as parameter')
            return
        ownername, value = input('onwnername: '), input('value: ')
        state = RecordState('Add', RegistroBrAPI.create_txt_record(ownername, value))
        items = self._records[domain]
        items.append(state)
        self._records.update({domain: items})

    def complete_new_txt_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    # def do_new_cname_record(self, args):
    #     ownername, server = input('onwnername: '), input('server: ')
    #     self._records.append(RegistroBrAPI.create_cname_record(ownername, server))

    # def do_new_a_record(self, args):
    #     ownername, ip = input('onwnername: '), input('ip: ')
    #     self._records.append(RegistroBrAPI.create_a_record(ownername, ip))

    # def do_new_aaaa_record(self, args):
    #     ownername, ipv6 = input('onwnername: '), input('ipv6: ')
    #     self._records.append(RegistroBrAPI.create_aaaa_record(ownername, ipv6))

    # def do_new_mx_record(self, args):
    #     ownername, priority, email_server = input('onwnername: '), input('value: '), input('email_server: ')
    #     self._records.append(RegistroBrAPI.create_mx_record(ownername, priority, email_server))

    # def do_new_tlsa_record(self, args):
    #     ownername, usage, selector, matching, data = input('ownername: '), input('usage: '), input('selector: '), input('matching: '), input('data: ')
    #     self._records.append(RegistroBrAPI.create_tlsa_record(ownername, usage, selector, matching, data))

    def do_delete_record(self, domain):
        'Delete records from a domain'
        if not domain:
            print('Please pass a domain as parameter')
            return
        for i, r in enumerate(self._records[domain]):
            print(i, r, sep=' - ')
        chosen = input('which ones to delete (comma separated)? ').split(',')
        for c in sorted(chosen, reverse=True):
            if self._records[domain][int(c)].State == 'Add':
                self._records[domain].remove(self._records[domain][int(c)])
            else:
                self._records[domain][int(c)].State = 'Delete'

    def complete_delete_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)



    def do_logout(self, args):
        if self._registrobr:
            print('Logging out of registro.br shell')
            self._registrobr.logout()
        else:
            print('You need to login first')

    def do_exit(self, args):
        self.do_logout(args)
        return True

if __name__ == '__main__':
    RegistroBrShell().cmdloop()
