r'''
Copyright 2014 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import logging
from nogotofail.mitm.connection.handlers.data import handlers
from nogotofail.mitm.connection.handlers.data import DataHandler
from nogotofail.mitm.connection.handlers.store import handler
from nogotofail.mitm.event import connection
from nogotofail.mitm.util import ssl2, tls, vuln

@handler(handlers, default=True)
class InsecureCipherDetectionHandler(DataHandler):
    name = "insecurecipherdetection"
    description = "Detect insecure ciphers in TLS Client Hellos"

    def _handle_bad_ciphers(self, ciphers, message):
            self.log(logging.ERROR, message)
            self.log_attack_event(data=ciphers)
            self.connection.vuln_notify(vuln.VULN_WEAK_CIPHER)

    def on_ssl(self, client_hello):

        # Check for anon ciphers, these don't verify the identity of the
        # endpoint
        anon_ciphers = [str(c) for c in client_hello.ciphers if "_anon_" in str(c)]
        if anon_ciphers:
            self._handle_bad_ciphers(anon_ciphers,
                "Client enabled anonymous TLS/SSL cipher suites %s" %
                (", ".join(anon_ciphers)))

        # Check for NULL encryption ciphers
        null_ciphers = [str(c) for c in client_hello.ciphers if "_WITH_NULL" in str(c)]
        if null_ciphers:
            self._handle_bad_ciphers(null_ciphers,
                "Client enabled NULL encryption TLS/SSL cipher suites %s" %
                (", ".join(null_ciphers)))

        # Check for NULL integrity ciphers
        integ_ciphers =  [str(c) for c in client_hello.ciphers if str(c).endswith("_NULL")]
        if integ_ciphers:
            self._handle_bad_ciphers(integ_ciphers,
                "Client enabled NULL integrity TLS/SSL cipher suites %s" %
                (", ".join(integ_ciphers)))


@handler(handlers, default=True)
class WeakTLSVersionDetectionHandler(DataHandler):
    name = "weaktlsversiondetection"
    description = "Detect versions of the TLS/SSL protocols that are known to be weak"

    def on_ssl(self, client_hello):
        if isinstance(client_hello, ssl2.types.ClientHello):
            self.log(logging.ERROR, "Client enabled SSLv2 protocol")
            self.log_attack_event(data="SSLv2")
            self.connection.vuln_notify(vuln.VULN_WEAK_TLS_VERSION)
            return
        if (isinstance(client_hello, tls.types.ClientHello) and
                client_hello.version.major == 3 and
                client_hello.version.minor == 0):
            self.log(logging.WARNING, "Client enabled SSLv3 protocol")
            self.log_attack_event(data="SSLv3")
            self.connection.vuln_notify(vuln.VULN_WEAK_TLS_VERSION)
            return
