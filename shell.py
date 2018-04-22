#!/usr/bin/env python3
import cmd
from registrobr import RegistroBrAPI
from getpass import getpass

class RegistroBrShell(cmd.Cmd):
    intro = 'Welcome to the registro.br shell. Type help or ? to list commands.\n'
    prompt = '(registro.br) '
    registrobr = None
    records = []
    loggedin = False

    def do_login(self, args):
        user = input('user: ')
        password = getpass('password: ')
        opt = input('otp: ')
        self.registrobr = RegistroBrAPI(user, password, opt)
        self.registrobr.login()
        self.loggedin = True
        print('Logged in')


    def do_domains(self, args):
        'List domains registered to this accounr'
        self._domains = self.registrobr.domains()
        for domain in self._domains:
            print(f'{domain.FQDN}')
    
    def do_zone_info(self, domain):
        'List zone info associated to this domain'
        if not self._domains:
            self._domains = self.registrobr.domains()
        filtered = filter(lambda d: d.FQDN == domain, self._domains)
        for domain in filtered:
            records = self.registrobr.zone_info(domain)
            print(*records, sep='\n')

    def complete_zone_info(self, text, line, begidx, endidx):
        if not self._domains:
            self._domains = self.registrobr.domains()
        filtered = filter(lambda d: d.FQDN.startswith(text), self._domains)
        mapped = [d.FQDN for d in filtered]
        return mapped

    def do_new_txt_record(self, args):
        ownername, value = input('onwnername: '), input('value: ')
        self.records.append(RegistroBrAPI.create_txt_record(ownername, value))

    def do_new_cname_record(self, args):
        ownername, server = input('onwnername: '), input('server: ')
        self.records.append(RegistroBrAPI.create_cname_record(ownername, server))

    def do_new_a_record(self, args):
        ownername, ip = input('onwnername: '), input('ip: ')
        self.records.append(RegistroBrAPI.create_a_record(ownername, ip))

    def do_new_aaaa_record(self, args):
        ownername, ipv6 = input('onwnername: '), input('ipv6: ')
        self.records.append(RegistroBrAPI.create_aaaa_record(ownername, ipv6))

    def do_new_mx_record(self, args):
        ownername, priority, email_server = input('onwnername: '), input('value: '), input('email_server: ')
        self.records.append(RegistroBrAPI.create_mx_record(ownername, priority, email_server))

    def do_new_tlsa_record(self, args):
        ownername, usage, selector, matching, data = input('ownername: '), input('usage: '), input('selector: '), input('matching: '), input('data: ')
        self.records.append(RegistroBrAPI.create_tlsa_record(ownername, usage, selector, matching, data))

    def do_delete_record(self, args):
        for i, r in enumerate(self.records):
            print(i, r, sep=' - ')
        chosen = input('which ones to delete (comma separated)? ').split(',')
        for c in sorted(chosen, reverse=True):
            self.records.remove(self.records[int(c)])

    def do_records(self, args):
        print(*self.records, sep='\n')

    def do_logout(self, args):
        if self.registrobr:
            print('Logging out of registro.br shell')
            self.registrobr.logout()
        else:
            print('You need to login first')

    def do_exit(self, args):
        if self.loggedin:
            self.do_logout(args)
        return True

if __name__ == '__main__':
    RegistroBrShell().cmdloop()
