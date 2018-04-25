#!/usr/bin/env python3

import argparse
import getpass
from registrobr import RegistroBrAPI

def config_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument('user')
    parser.add_argument('-p', '--password')
    parser.add_argument('-o', '--otp')
    commands = parser.add_subparsers(title='Commands', dest='command')
    commands.required = True

    commands.add_parser('domains', help='List domains for this user')

    zone_info_parser = commands.add_parser(
        'zone_info', help='List Zone Info for the domain')
    zone_info_parser.add_argument('domain')

    add_record_parser = commands.add_parser(
        'add_record', help='List domains for this user')
    add_record_parser.add_argument('domain')
    add_record_parser.add_argument('type')
    add_record_parser.add_argument('ownername')
    add_record_parser.add_argument('value')

    return parser


def main():
    ARGS = config_argparse().parse_args()

    if not ARGS.password:
        ARGS.password = getpass.getpass()

    # if not ARGS.otp:
        # ARGS.otp = input('OTP: ')
    
    registrobr = RegistroBrAPI(ARGS.user, ARGS.password, ARGS.otp)

    registrobr.login()

    if ARGS.command == 'domains':
        domains = registrobr.domains()
        for domain in domains:
            print(f'Domínio: {domain.FQDN} - Status: {domain.Status} - Expira em: {domain.ExpirationDate}')
    elif ARGS.command == 'zone_info':
        domains = registrobr.domains()
        filtered = filter(lambda d: d.FQDN == ARGS.domain, domains)
        for domain in filtered:
            records = registrobr.zone_info(domain)
            print(*records, sep='\n')
    elif ARGS.command == 'add_record':
        if ARGS.type.upper() == 'A':
            record=registrobr.create_a_record(ARGS.ownername, ARGS.value)
            registrobr.add_records(ARGS.domain, [record])
        elif ARGS.type.upper() == 'AAA':
            record=registrobr.create_aaaa_record(ARGS.ownername, ARGS.value)
            registrobr.add_records(ARGS.domain, [record])
        elif ARGS.type.upper() == 'record':
            record=registrobr.create_txt_record(ARGS.ownername, ARGS.value)
            registrobr.add_records(ARGS.domain, [record])
        elif ARGS.type.upper() == 'CNAME':
            record=registrobr.create_cname_record(ARGS.ownername, ARGS.value)
            registrobr.add_records(ARGS.domain, [record])
        elif ARGS.type.upper() == 'MX':
            record=registrobr.create_mx_record(ARGS.ownername, **ARGS.value.split())
            registrobr.add_records(ARGS.domain, [record])
        elif ARGS.type.upper() == 'TLSA':
            record=registrobr.create_tlsa_record(ARGS.ownername, **ARGS.value.split())
            registrobr.add_records(ARGS.domain, [record])

    registrobr.logout()


if __name__ == '__main__':
    main()
