#!/usr/bin/env python3
import cmd
from registrobr import RegistroBrAPI, create_txt_record, create_a_record, create_aaaa_record, create_cname_record, create_mx_record, create_tlsa_record
from registrobr.registrobr import _DOMAIN
from getpass import getpass
from collections import namedtuple
from pprint import pprint
import operator
from colorama import init, Fore, Style

class RecordState:
    'Represents the state of the record on registro.br'

    def __init__(self, record, state='Unchanged'):
        self.State = state
        self.Record = record

    def __str__(self):
        return f'RecordState(State={self.State}, Record={self.Record})'


class RegistroBrShell(cmd.Cmd):
    intro = 'Welcome to the registro.br shell. Type help or ? to see a list of commands.\n'
    _default_prompt = f'{Style.BRIGHT+Fore.GREEN}registro.br{Style.RESET_ALL}'
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
        domain2 = _DOMAIN(2, 'ubuntu.name', 'expiry',
                         'status', 'contact', 'paylink', False)
        self._domains = [domain, domain2]

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
        mock_records2 = [
            RecordState(create_txt_record('*', 'ubuntu name generator'))            
        ]

        self._registrobr = RegistroBrAPI('mock')
        self._user = 'mock'
        self._registrobr.is_logged = True
        self._records.update({domain.FQDN: mock_records})
        self._records.update({domain2.FQDN: mock_records2})

    def postcmd(self, stop, line):
        self.set_prompt()
        return stop

    def set_prompt(self):
        logged = ""
        context = self._context
        if context:
            context = f' - {Style.BRIGHT+Fore.RED}{context}{Style.RESET_ALL}'
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

    def logged_in(self):
        if (self._user == 'mock'):
            print('Can\'t do this while mocking!')
            return False
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return False
        return True

    def ensure_domains(self, force=False):
        if not self._domains or force:
            self._domains = self._registrobr.domains()
    
    def ensure_records(self, domain, force=False):
        self.ensure_domains()
        domain_obj = [ d for d in self._domains if d.FQDN == domain ][0]
        if domain not in self._records or force:
            records = self._registrobr.zone_info(domain_obj)
            records_with_state = list(map(RecordState, records))
            self._records.update({domain_obj.FQDN: records_with_state})

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
        if not self.logged_in():
            return
        self.ensure_domains(force)
        for domain in self._domains:
            print(f'{domain.FQDN}')

    def do_refresh_zone_info(self, domain):
        if not self.logged_in(): 
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        self.ensure_records(domain, force=True)
    
    def complete_refresh_zone_info(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_zone_info(self, domain):
        'List records associated to this domain'
        if not (self._registrobr and self._registrobr.is_logged):
            print('Please log in first!')
            return
        domain = self.check_domain(domain)
        if not domain:
            return
        self.ensure_domains()
        filtered = [ d for d in self._domains if d.FQDN == domain ]
        for domain_obj in filtered:
            if domain_obj.FQDN not in self._records:
                self.ensure_records(domain_obj.FQDN)
            print_records(self._records[domain_obj.FQDN])

    def help_zone_info(self):                                     
        print(f'''List zone info records for the selected domain

{'Type':^12} | {'Data':^53}
  TXT_RECORD | ownername - data
   MX_RECORD | ownername - priority - email_server
CNAME_RECORD | ownername - server
 TLSA_RECORD | ownername - usage - selector - matching - data'
    A_RECORD | ownername - IPv4
 AAAA_RECORD | ownername - IPv6

For TLSA_RECORD:
usage = 0: 'CA'
        1: 'Service certificate'
        2: 'Trust Anchor'
        3: 'Dom-issued certificate'

selector = 0: 'Subject Public Key'
           1: 'Subject Public Key'

matching = 1: 'SHA-256'
           2: 'SHA-512'
''')

    def domains_completion(self, text):
        self.ensure_domains()
        filtered = filter(lambda d: d.FQDN.startswith(text), self._domains)
        mapped = [d.FQDN for d in filtered]
        return mapped

    def complete_zone_info(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def do_save(self, domain):
        'Save records for a domain'
        domain = self.check_domain(domain)
        if not domain:
            return

        d = [d for d in self._domains if d.FQDN == domain]
        added_deleted = [ record for record in self._records[d[0].FQDN] if record.State != 'Unchanged' ]

        print_records(added_deleted)

        records_to_add = []
        records_to_delete = []
        for record_state in added_deleted:
            ownername = list(record_state.Record._asdict().values())[0]
            rest = '+'.join(list(map(str, record_state.Record._asdict().values()))[1:])
            _type = record_state.Record.__class__.__name__.replace('_RECORD', '')
            record = '|'.join([ownername, _type, rest.replace(' ', '+')])
            if record_state.State == 'Add':
                records_to_add.append(record)
            if record_state.State == 'Delete':
                records_to_delete.append(record)

        if records_to_add:
            print(records_to_add)
            self._registrobr.add_records(domain, records_to_add)
        if records_to_delete:
            print(records_to_delete)
            self._registrobr.remove_records(domain, records_to_delete)

    def complete_save(self, text, line, begidx, endidx):
        return self.domains_completion(text)

    def record_to_text(self, r):
        if isinstance(r, create_txt_record(None, None)):
            print('TXT')
    
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
        self.ensure_records(domain)
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
    color = Style.BRIGHT+Fore.YELLOW
    if state == 'Delete':
        color = Style.BRIGHT+Fore.RED
    elif state == 'Add':
        color = Style.BRIGHT+Fore.BLUE
    return f'{color}{state:<9}{Style.RESET_ALL} | {type:>12} | {data:<53}'


def record_values(record):
    values = []
    for field in record._fields:
        value = getattr(record, field)
        values.append(f'{value}')
    return " - ".join(values)


def main():
    init()
    RegistroBrShell().cmdloop()


if __name__ == '__main__':
    main()
