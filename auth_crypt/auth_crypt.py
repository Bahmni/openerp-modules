#
# Implements encrypting functions.
#
# Copyright (c) 2008, F S 3 Consulting Inc.
#
# Maintainer:
# Alec Joseph Rivera (agi<at>fs3.ph)
# refactored by Antony Lesuisse <al<at>openerp.com>
#

import hashlib
import hmac
import logging
from random import sample
from string import ascii_letters, digits

import openerp
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

magic_md5 = '$1$'
magic_sha256 = '$5$'

def gen_salt(length=8, symbols=None):
    if symbols is None:
        symbols = ascii_letters + digits
    return ''.join(sample(symbols, length))

def md5crypt( raw_pw, salt, magic=magic_md5 ):
    """ md5crypt FreeBSD crypt(3) based on but different from md5

    The md5crypt is based on Mark Johnson's md5crypt.py, which in turn is
    based on  FreeBSD src/lib/libcrypt/crypt.c (1.2)  by  Poul-Henning Kamp.
    Mark's port can be found in  ActiveState ASPN Python Cookbook.  Kudos to
    Poul and Mark. -agi

    Original license:

    * "THE BEER-WARE LICENSE" (Revision 42):
    *
    * <phk@login.dknet.dk>  wrote  this file.  As  long as  you retain  this
    * notice  you can do  whatever you want with this stuff. If we meet some
    * day,  and you think this stuff is worth it,  you can buy me  a beer in
    * return.
    *
    * Poul-Henning Kamp
    """
    raw_pw = raw_pw.encode('utf-8')
    salt = salt.encode('utf-8')
    hash = hashlib.md5()
    hash.update( raw_pw + magic + salt )
    st = hashlib.md5()
    st.update( raw_pw + salt + raw_pw)
    stretch = st.digest()

    for i in range( 0, len( raw_pw ) ):
        hash.update( stretch[i % 16] )

    i = len( raw_pw )

    while i:
        if i & 1:
            hash.update('\x00')
        else:
            hash.update( raw_pw[0] )
        i >>= 1

    saltedmd5 = hash.digest()

    for i in range( 1000 ):
        hash = hashlib.md5()

        if i & 1:
            hash.update( raw_pw )
        else:
            hash.update( saltedmd5 )

        if i % 3:
            hash.update( salt )
        if i % 7:
            hash.update( raw_pw )
        if i & 1:
            hash.update( saltedmd5 )
        else:
            hash.update( raw_pw )

        saltedmd5 = hash.digest()

    itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    rearranged = ''
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
        v = ord( saltedmd5[a] ) << 16 | ord( saltedmd5[b] ) << 8 | ord( saltedmd5[c] )

        for i in range(4):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

    v = ord( saltedmd5[11] )

    for i in range( 2 ):
        rearranged += itoa64[v & 0x3f]
        v >>= 6

    return magic + salt + '$' + rearranged

def sh256crypt(cls, password, salt, magic=magic_sha256):
    iterations = 1000
    # see http://en.wikipedia.org/wiki/PBKDF2
    result = password.encode('utf8')
    for i in xrange(cls.iterations):
        result = hmac.HMAC(result, salt, hashlib.sha256).digest() # uses HMAC (RFC 2104) to apply salt
    result = result.encode('base64') # doesnt seem to be crypt(3) compatible
    return '%s%s$%s' % (magic_sha256, salt, result)

class res_users(osv.osv):
    _inherit = "res.users"

    _columns = {
        'password_crypt': fields.char(string='Encrypted Password', invisible=True),
    }

    def check_credentials(self, cr, uid, password):
        # convert to base_crypt if needed
        cr.execute('SELECT password, password_crypt FROM res_users WHERE id=%s AND active', (uid,))
        if password and cr.rowcount:
            stored_password, stored_password_crypt = cr.fetchone()
            if password and not stored_password_crypt:
                salt = gen_salt()
                stored_password_crypt = md5crypt(stored_password, salt)
                cr.execute("UPDATE res_users SET password='', password_crypt=%s WHERE id=%s", (stored_password_crypt, uid))
            if stored_password_crypt:
                salt = self.get_salt_from(stored_password_crypt)
                if stored_password_crypt == md5crypt(password, salt):
                    return

        raise openerp.exceptions.AccessDenied()


    def write(self, cr, uid, ids, values, context=None):
        if(values.get('password')):
            values['password_crypt'] = md5crypt(values.get('password'), gen_salt())
            values['password'] = ''
        return super(res_users, self).write(cr, uid, ids, values, context)


    def get_salt_from(self,password):
        if password[:len(magic_md5)] == magic_md5:
            return password[len(magic_md5):11]

        elif password[:len(magic_md5)] == magic_sha256:
            return password[len(magic_md5):11]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
