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

    domains_parser = commands.add_parser(
        'domains', help='List domains for this user')

    zone_info_parser = commands.add_parser(
        'zone_info', help='List Zone Info for the domain')
    zone_info_parser.add_argument('domain')

    return parser


def main():
    ARGS = config_argparse().parse_args()

    if not ARGS.password:
        ARGS.password = getpass.getpass()

    if not ARGS.otp:
        ARGS.otp = input('OTP: ')
    
    registrobr = RegistroBr(ARGS.user, ARGS.password, ARGS.otp)

    registrobr.login()

    if ARGS.command == 'domains':
        domains = registrobr.domains()
        for domain in domains:
            print(
                f'Domínio {domain["FQDN"]} com status {domain["Status"]} expira em: {domain["ExpirationDate"]}')
    elif ARGS.command == 'zone_info':
        domains = registrobr.domains()
        filtered = filter(lambda d: d['FQDN'] == ARGS.domain, domains)
        for domain in filtered:
            registrobr.zone_info(domain)

    # txt=registrobr.create_txt_record('owner', 'qualquer texto')

    # registrobr.add_records(domains[0], [txt])

    # registrobr.zone_info(domains[0])

    registrobr.logout()


if __name__ == '__main__':
    main()
