#!/usr/bin/env python3
import cmd
from registrobr import RegistroBrAPI, create_txt_record, create_a_record, create_aaaa_record, create_cname_record, create_mx_record, create_tlsa_record
from registrobr.registrobr import _DOMAIN
from getpass import getpass
from collections import namedtuple
from pprint import pprint
import operator


class RecordState:
    'Represents the state of the record on registro.br'

    def __init__(self, record, state='Unchanged'):
        self.State = state
        self.Record = record

    def __str__(self):
        return f'RecordState(State={self.State}, Record={self.Record})'


_FORMATTERS = {
    'BOLD': '\033[1m',
    'BLACK': '\033[30m',
    'BLACKBG': '\033[40m',
    'RED': '\033[31m',
    'REDBG': '\033[41m',
    'GREEN': '\033[32m',
    'GREENBG': '\033[42m',
    'YELLOW': '\033[33m',
    'YELLOWBG': '\033[43m',
    'BLUE': '\033[34m',
    'BLUEBG': '\033[44m',
    'MAGENTA': '\033[35m',
    'MAGENTABG': '\033[45m',
    'CYAN': '\033[36m',
    'CYANBG': '\033[46m',
    'WHITE': '\033[37m',
    'WHITEBG': '\033[47m',
    'RESET': '\033[39m',
    'RESETBG': '\033[49m',
    'RESETALL': '\033[0m'
}


class RegistroBrShell(cmd.Cmd):
    intro = 'Welcome to the registro.br shell. Type help or ? to see a list of commands.\n'
    _default_prompt = f'{_FORMATTERS["GREEN"]}registro.br{_FORMATTERS["RESETALL"]}'
    prompt = f'{_default_prompt}> '
    _registrobr = None
    _records = dict()
    _domains = []
    _selected_domain = None
    _context = ''

    def __init__(self):
        super().__init__()
        self.set_prompt()

    def do_mock(self, args):
        'Development mock'
        domain = _DOMAIN(1, 'crespo.com.br', 'expiry',
                         'status', 'contact', 'paylink', False)
        self._domains = [domain]

        mock_records = [
            RecordState(create_txt_record('_acme-challenge',
                                          'LupjAATGvUdOtoofGU4j_TK4WsZM5omLSuc5txLndfg')),
            RecordState(create_tlsa_record('_test', usage=0, selector=1,
                                           matching=1, data='d2abde240d7cd3ee6b4b28c54df034b9')),
            RecordState(create_mx_record('_test_mx', 10, 'test.mx.record')),
            RecordState(create_cname_record(
                ownername='fernando', server='fcrespo82.github.io')),
            RecordState(create_cname_record(
                ownername='blog.fernando', server='fcrespo82.github.io')),
            RecordState(create_cname_record(
                ownername='curriculo.fernando', server='fcrespo82.github.io')),
            RecordState(create_cname_record(
                ownername='nas', server='fcrespo82.myds.me')),
            RecordState(create_txt_record(ownername='_dnsauth.nas',
                                          data='201803271600392msn9aiznnhm90owmz8d5nc5nddaroa8gv5w7ca7czm2dxcm4c')),
            RecordState(create_txt_record('owner', 'qualquer texto'))
        ]

        self._registrobr = RegistroBrAPI('mock')
        self._user = 'mock'
        self._registrobr.is_logged = True
        self._records.update({domain.FQDN: mock_records})

    def postcmd(self, stop, line):
        self.set_prompt()
        return stop

    def set_prompt(self):
        logged = ""
        context = self._context
        if context:
            context = f' - {_FORMATTERS["RED"]}{context}{_FORMATTERS["RESETALL"]}'
        if self._registrobr and self._registrobr.is_logged:
            logged = f' ({self._user})'

        self.prompt = f'{self._default_prompt}{logged}{context}> '

    def check_domain(self, domain):
        if self._selected_domain:
            domain = self._selected_domain.FQDN
        if not domain:
            print('Please pass a domain as parameter or use \'use\' keyword')
            return None
        return domain

    def ensure_domains(self, force=False):
        if not self._domains or force:
            self._domains = self._registrobr.domains()

    def do_login(self, _):
        'Login to registro.br'
        if self._registrobr and self._registrobr.is_logged:
            print('Already logged in, please log out first')
        else:
            user = input('User: ')
            self._registrobr = RegistroBrAPI(user)
            self._registrobr.login()
            self._user = user
            print('Logged in')

    def do_use(self, domain):
        'Select a domain to use as a context'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        self.ensure_domains()
        if domain:
            found = list(filter(lambda d: d.FQDN == domain, self._domains))
            if found:
                self._selected_domain = found[0]
                self._context = self._selected_domain.FQDN
            else:
                print(
                    'Please try again. Use one of the indexes above or pass a valid FQDN.')
        else:
            for index, domain in enumerate(self._domains):
                print(index, domain.FQDN, sep=' - ')
            chosen = input('Which domain to use? ')
            try:
                id = int(chosen)
                self._selected_domain = self._domains[id]
                self._context = self._selected_domain.FQDN
            except:
                print(
                    'Please try again. Use one of the indexes above or pass a valid FQDN.')

    def complete_use(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_stop_using(self, _):
        'Remove domain context'
        self._selected_domain = None
        self._context = ""

    def do_domains(self, force):
        'List domains registered to this account'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        self.ensure_domains(force)
        for domain in self._domains:
            print(f'{domain.FQDN}')

    def do_zone_info(self, domain):
        'List records associated to this domain'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        self.ensure_domains()
        filtered = filter(lambda d: d.FQDN == domain, self._domains)
        for domain_obj in filtered:
            if domain_obj.FQDN not in self._records:
                records = self._registrobr.zone_info(domain_obj)
                records_with_state = list(map(RecordState, records))
                self._records.update({domain_obj.FQDN: records_with_state})
            for key in self._records:
                print(f'{f" {key} ":=^80}')
                sorted_records = sorted(
                    self._records[key], key=operator.attrgetter('Record.__class__.__name__'))
                print_records(sorted_records)

    def help_zone_info(self):
        pass

    def domains_completion(self, text):
        self.ensure_domains()
        filtered = filter(lambda d: d.FQDN.startswith(text), self._domains)
        mapped = [d.FQDN for d in filtered]
        return mapped

    def complete_zone_info(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_records(self, domain):
        'List records from a domain or all domains'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if domain:
            filtered = [d for d in self._records if d == domain]
        else:
            filtered = self._records

        for domain_key in filtered:
            domain_key_spaced = f' {domain_key} '
            print(f'{domain_key_spaced:=^80}')
            for recordState in self._records[domain_key]:
                print(recordState)
            print(80*'=')

    def complete_records(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_txt_record(self, domain):
        'Create a TXT record'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        ownername, value = input('onwnername: '), input('value: ')
        state = RecordState(create_txt_record(ownername, value), 'Add')
        self._records[domain].append(state)

    def complete_new_txt_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_cname_record(self, domain):
        'Create a CNAME record'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        ownername, server = input('onwnername: '), input('server: ')
        state = RecordState(create_cname_record(ownername, server), 'Add')
        self._records[domain].append(state)

    def complete_new_cname_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_a_record(self, domain):
        'Create a A record'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        ownername, ip = input('onwnername: '), input('IP v4: ')
        state = RecordState(create_a_record(ownername, ip), 'Add')
        self._records[domain].append(state)

    def complete_new_a_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_aaaa_record(self, domain):
        'Create a AAAA record'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        ownername, ipv6 = input('onwnername: '), input('IP v6: ')
        state = RecordState(create_aaaa_record(ownername, ipv6), 'Add')
        self._records[domain].append(state)

    def complete_new_aaaa_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_mx_record(self, domain):
        'Create a MX record'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        ownername, priority, email_server = input(
            'onwnername: '), input('value: '), input('email_server: ')
        state = RecordState(create_mx_record(
            ownername, priority, email_server), 'Add')
        self._records[domain].append(state)

    def complete_new_mx_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_new_tlsa_record(self, domain):
        'Create a TLSA record'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        ownername, usage, selector, matching, data = input('ownername: '), input(
            'usage: '), input('selector: '), input('matching: '), input('data: ')
        state = RecordState(create_tlsa_record(
            ownername, usage, selector, matching, data), 'Add')
        self._records[domain].append(state)

    def complete_new_tlsa_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_delete_record(self, domain):
        'Delete records from a domain'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        for i, r in enumerate(self._records[domain]):
            print(i, record_line(r.State, r.Record.__class__.__name__, r.Record), sep=' - ')
        chosen = input('which ones to delete (comma separated)? ').split(',')
        for c in sorted(chosen, reverse=True):
            if self._records[domain][int(c)].State == 'Add':
                self._records[domain].remove(self._records[domain][int(c)])
            else:
                self._records[domain][int(c)].State = 'Delete'

    def complete_delete_record(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_logout(self, args):
        'Log out of registro.br'
        if self._registrobr and self._registrobr.is_logged:
            print('Logging out of registro.br')
            self._registrobr.logout()
            self._registrobr = None
            self._records = dict()
            self._domains = []
            self._selected_domain = None
            self._context = ''
        else:
            print('You need to login first')

    def do_exit(self, args):
        'Close registro.br shell logging out if necessary'
        self.do_logout(args)
        return True


def print_records(records):
    print(f'{"State":^9} | {"Type":^12} | {"Data":^53}')
    for record_state in records:
        print(record_line(record_state.State,
                   record_state.Record.__class__.__name__, record_state.Record))


def record_line(state, type, record):
    data = record_values(record)
    return f'{state:<9} | {type:>12} | {data:<53}'


def record_values(record):
    values = []
    for field in record._fields:
        value = getattr(record, field)
        values.append(f'{value}')
    return " - ".join(values)


def main():
    RegistroBrShell().cmdloop()


if __name__ == '__main__':
    main()
