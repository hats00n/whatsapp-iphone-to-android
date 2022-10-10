from re import findall


def parse_jid_string(jid_string: str) -> dict:
    """
    Parses the jid_string into a dictionary with keys `user`, `server`, basically splits the string with `@`
    :param jid_string: the raw_jid_string e.g. 3112312312312@s.whatsapp.com
    """
    pat = "^([^@]*)@([^@]*)$"
    ret = findall(pat, jid_string)
    if not ret:
        raise ValueError("{} not in USER_ID@SERVER_ADDRESS format".format(jid_string))
    return {
        'user': ret[0][0],
        'server': ret[0][1]
    }
