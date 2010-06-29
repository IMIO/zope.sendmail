##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Classes which abstract different channels a message could be sent to.
"""
__docformat__ = 'restructuredtext'

import socket
from smtplib import SMTP

from zope.interface import implements
from zope.sendmail.interfaces import ISMTPMailer

have_ssl = hasattr(socket, 'ssl')

class SMTPMailer(object):

    implements(ISMTPMailer)

    smtp = SMTP

    def __init__(self, hostname='localhost', port=25,
                 username=None, password=None, no_tls=False, force_tls=False):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.force_tls = force_tls
        self.no_tls = no_tls
        self.connection = None

    def vote(self, fromaddr, toaddrs, message):
        self.connection = self.smtp(self.hostname, str(self.port))

        code, response = self.connection.ehlo()
        if code < 200 or code >= 300:
            code, response = self.connection.helo()
            if code < 200 or code >= 300:
                raise RuntimeError('Error sending HELO to the SMTP server '
                                   '(code=%s, response=%s)' % (code, response))
        
        self.code, self.response = code, response


    def abort(self):
        if self.connection is None:
            return
        
        try:
            self.connection.quit()
        except socket.sslerror:
            #something weird happened while quiting
            self.connection.close()

    def send(self, fromaddr, toaddrs, message):
        connection = getattr(self, 'connection', None)
        if connection is None:
            self.vote(fromaddr, toaddrs, message)

        connection, code, response = self.connection, self.code, self.response
            

        # encryption support
        have_tls =  connection.has_extn('starttls')
        if not have_tls and self.force_tls:
            raise RuntimeError('TLS is not available but TLS is required')

        if have_tls and have_ssl and not self.no_tls:
            connection.starttls()
            connection.ehlo()

        if connection.does_esmtp:
            if self.username is not None and self.password is not None:
                connection.login(self.username, self.password)
        elif self.username:
            raise RuntimeError('Mailhost does not support ESMTP but a username '
                                'is configured')

        connection.sendmail(fromaddr, toaddrs, message)
        try:
            connection.quit()
        except socket.sslerror:
            #something weird happened while quiting
            connection.close()
