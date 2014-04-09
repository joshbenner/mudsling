"""
ANSI adapted from Evennia. Original ANSI code LICENSE:

BSD license
===========

Copyright (c) 2012-, Griatch (griatch <AT> gmail <DOT> com), Gregory Taylor
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

- Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
- Neither the name of the Copyright Holders nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
import textwrap
import re
import operator
from collections import namedtuple


__all__ = ['ANSI_PARSER', 'AnsiWrapper', 'wrap', 'fill', 'parse_ansi',
           'strip_ansi', 'escape_ansi_tokens', 'strip_ansi_tokens', 'length',
           'center', 'ljust', 'rjust', 'endswith', 'startswith', 'linewrap']


# ANSI definitions
ANSI_BEEP = "\07"
ANSI_ESCAPE = "\033"
ANSI_NORMAL = "\033[0m"

ANSI_UNDERLINE = "\033[4m"
ANSI_HILITE = "\033[1m"
ANSI_ITALIC = "\033[3m"
ANSI_BLINK = "\033[5m"
ANSI_INVERSE = "\033[7m"
ANSI_INV_HILITE = "\033[1;7m"
ANSI_INV_BLINK = "\033[7;5m"
ANSI_BLINK_HILITE = "\033[1;5m"
ANSI_INV_BLINK_HILITE = "\033[1;5;7m"

# Foreground colors
ANSI_BLACK = "\033[30m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"
ANSI_WHITE = "\033[37m"

# Background colors
ANSI_BACK_BLACK = "\033[40m"
ANSI_BACK_RED = "\033[41m"
ANSI_BACK_GREEN = "\033[42m"
ANSI_BACK_YELLOW = "\033[43m"
ANSI_BACK_BLUE = "\033[44m"
ANSI_BACK_MAGENTA = "\033[45m"
ANSI_BACK_CYAN = "\033[46m"
ANSI_BACK_WHITE = "\033[47m"

# Formatting Characters
ANSI_RETURN = "\r\n"
ANSI_TAB = "\t"
ANSI_SPACE = " "

# Escapes
ANSI_ESCAPES = ("{{", "%%", "\\\\")


class ANSIState(namedtuple('ANSIState', 'bg fg special')):
    def update(self, state):
        replacements = {}
        if self.special == 'n':
            return state
        for attr in ['bg', 'fg', 'special']:
            v = getattr(state, attr)
            if v is not None:
                replacements[attr] = v
        return self._replace(**replacements)


class ANSIParser(object):
    """
    A class that parses ansi markup
    to ANSI command sequences

    We also allow to escape colour codes
    by prepending with a \ for mux-style and xterm256,
    an extra { for Merc-style codes
    """

    def __init__(self):
        # Sets the mappings

        # MUX-style mappings %cr %cn etc
        self.mux_ansi_map = [
            # commented out by default; they are potentially annoying
            (r'%r', ANSI_RETURN),
            (r'%t', ANSI_TAB),
            (r'%b', ANSI_SPACE),
            #(r'%cf', ANSI_BLINK),
            #(r'%ci', ANSI_INVERSE),
            (r'%cr', ANSI_RED),
            (r'%cR', ANSI_BACK_RED),
            (r'%cg', ANSI_GREEN),
            (r'%cG', ANSI_BACK_GREEN),
            (r'%cy', ANSI_YELLOW),
            (r'%cY', ANSI_BACK_YELLOW),
            (r'%cb', ANSI_BLUE),
            (r'%cB', ANSI_BACK_BLUE),
            (r'%cm', ANSI_MAGENTA),
            (r'%cM', ANSI_BACK_MAGENTA),
            (r'%cc', ANSI_CYAN),
            (r'%cC', ANSI_BACK_CYAN),
            (r'%cw', ANSI_WHITE),
            (r'%cW', ANSI_BACK_WHITE),
            (r'%cx', ANSI_BLACK),
            (r'%cX', ANSI_BACK_BLACK),
            (r'%ch', ANSI_HILITE),
            (r'%cn', ANSI_NORMAL),
        ]

        # Expanded mapping {r {n etc
        hilite = ANSI_HILITE
        normal = ANSI_NORMAL
        self.ext_ansi_map = [
            (r'{u', ANSI_UNDERLINE),
            (r'{i', ANSI_ITALIC),
            (r'{r', hilite + ANSI_RED),
            (r'{R', ANSI_RED),
            (r'{_r', ANSI_BACK_RED),
            (r'{g', hilite + ANSI_GREEN),
            (r'{G', ANSI_GREEN),
            (r'{_g', ANSI_BACK_GREEN),
            (r'{y', hilite + ANSI_YELLOW),
            (r'{Y', ANSI_YELLOW),
            (r'{_y', ANSI_BACK_YELLOW),
            (r'{b', hilite + ANSI_BLUE),
            (r'{B', ANSI_BLUE),
            (r'{_b', ANSI_BACK_BLUE),
            (r'{m', hilite + ANSI_MAGENTA),
            (r'{M', ANSI_MAGENTA),
            (r'{_m', ANSI_BACK_MAGENTA),
            (r'{c', hilite + ANSI_CYAN),
            (r'{C', ANSI_CYAN),
            (r'{_c', ANSI_BACK_CYAN),
            (r'{w', hilite + ANSI_WHITE),  # pure white
            (r'{W', ANSI_WHITE),  # light grey
            (r'{_w', ANSI_BACK_WHITE),
            (r'{x', hilite + ANSI_BLACK),  # dark grey
            (r'{X', ANSI_BLACK),  # pure black
            (r'{_x', ANSI_BACK_BLACK),
            (r'{n', normal)                # reset
        ]

        # xterm256 {123, %c134,
        self.xterm256_map = [
            (r'{([0-9]{1,3})', self.parse_xterm256),  # {123 - fg color
            (r'{(_[0-9]{1,3})', self.parse_xterm256)  # {_123 - bg color
        ]

        # prepare regex matching
        self.ansi_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                         for sub in self.ext_ansi_map]
        self.ansi_map = self.ext_ansi_map
        self.xterm256_sub = [(re.compile(r, re.DOTALL), f)
                             for r, f in self.xterm256_map]
        self.xterm256_regex = re.compile(r'\{(_?\d{1,3})', re.DOTALL)

        # prepare matching ansi codes overall
        self.ansi_regex = re.compile("\033\[[0-9;]+m")

        # escapes - replace doubles with a single instance of each
        self.ansi_escapes = re.compile(r"(%s)" % "|".join(ANSI_ESCAPES),
                                       re.DOTALL)

        tokens = [r'\{_?\d{1,3}']
        for regex, sub in self.xterm256_map:
            regex = regex.replace('(', '').replace(')', '')
            tokens.append(regex)
        for token, sub in self.ansi_map:
            tokens.append(re.escape(token))
        token_pat = r'(?<!\{)(?:' + '|'.join(tokens) + ')'
        self._token_regex = re.compile(token_pat)
        self.token_regex = re.compile('(%s)' % token_pat)

        self.compound_regex = re.compile('(%s)' % (token_pat
                                                   + '|'
                                                   + self.ansi_regex.pattern))
        self.parse_token_regex = re.compile(
            r'\{(?:_(?P<bg>[rgybmcwx]|\d{1,3})'
            r'|(?P<fg>[rRgGyYbBmMcCwWxX]|\d{1,3})'
            r'|(?P<special>[nui]))')

        self.ansi_hex = [
            # Primary 3-bit (8 colors).
            ('00',  '000000'),
            ('01',  '800000'),
            ('02',  '008000'),
            ('03',  '808000'),
            ('04',  '000080'),
            ('05',  '800080'),
            ('06',  '008080'),
            ('07',  'c0c0c0'),

            # Equivalent "bright" versions of original 8 colors.
            ('08',  '808080'),
            ('09',  'ff0000'),
            ('10',  '00ff00'),
            ('11',  'ffff00'),
            ('12',  '0000ff'),
            ('13',  'ff00ff'),
            ('14',  '00ffff'),
            ('15',  'ffffff'),

            # Strictly ascending.
            ('16',  '000000'),
            ('17',  '00005f'),
            ('18',  '000087'),
            ('19',  '0000af'),
            ('20',  '0000d7'),
            ('21',  '0000ff'),
            ('22',  '005f00'),
            ('23',  '005f5f'),
            ('24',  '005f87'),
            ('25',  '005faf'),
            ('26',  '005fd7'),
            ('27',  '005fff'),
            ('28',  '008700'),
            ('29',  '00875f'),
            ('30',  '008787'),
            ('31',  '0087af'),
            ('32',  '0087d7'),
            ('33',  '0087ff'),
            ('34',  '00af00'),
            ('35',  '00af5f'),
            ('36',  '00af87'),
            ('37',  '00afaf'),
            ('38',  '00afd7'),
            ('39',  '00afff'),
            ('40',  '00d700'),
            ('41',  '00d75f'),
            ('42',  '00d787'),
            ('43',  '00d7af'),
            ('44',  '00d7d7'),
            ('45',  '00d7ff'),
            ('46',  '00ff00'),
            ('47',  '00ff5f'),
            ('48',  '00ff87'),
            ('49',  '00ffaf'),
            ('50',  '00ffd7'),
            ('51',  '00ffff'),
            ('52',  '5f0000'),
            ('53',  '5f005f'),
            ('54',  '5f0087'),
            ('55',  '5f00af'),
            ('56',  '5f00d7'),
            ('57',  '5f00ff'),
            ('58',  '5f5f00'),
            ('59',  '5f5f5f'),
            ('60',  '5f5f87'),
            ('61',  '5f5faf'),
            ('62',  '5f5fd7'),
            ('63',  '5f5fff'),
            ('64',  '5f8700'),
            ('65',  '5f875f'),
            ('66',  '5f8787'),
            ('67',  '5f87af'),
            ('68',  '5f87d7'),
            ('69',  '5f87ff'),
            ('70',  '5faf00'),
            ('71',  '5faf5f'),
            ('72',  '5faf87'),
            ('73',  '5fafaf'),
            ('74',  '5fafd7'),
            ('75',  '5fafff'),
            ('76',  '5fd700'),
            ('77',  '5fd75f'),
            ('78',  '5fd787'),
            ('79',  '5fd7af'),
            ('80',  '5fd7d7'),
            ('81',  '5fd7ff'),
            ('82',  '5fff00'),
            ('83',  '5fff5f'),
            ('84',  '5fff87'),
            ('85',  '5fffaf'),
            ('86',  '5fffd7'),
            ('87',  '5fffff'),
            ('88',  '870000'),
            ('89',  '87005f'),
            ('90',  '870087'),
            ('91',  '8700af'),
            ('92',  '8700d7'),
            ('93',  '8700ff'),
            ('94',  '875f00'),
            ('95',  '875f5f'),
            ('96',  '875f87'),
            ('97',  '875faf'),
            ('98',  '875fd7'),
            ('99',  '875fff'),
            ('100', '878700'),
            ('101', '87875f'),
            ('102', '878787'),
            ('103', '8787af'),
            ('104', '8787d7'),
            ('105', '8787ff'),
            ('106', '87af00'),
            ('107', '87af5f'),
            ('108', '87af87'),
            ('109', '87afaf'),
            ('110', '87afd7'),
            ('111', '87afff'),
            ('112', '87d700'),
            ('113', '87d75f'),
            ('114', '87d787'),
            ('115', '87d7af'),
            ('116', '87d7d7'),
            ('117', '87d7ff'),
            ('118', '87ff00'),
            ('119', '87ff5f'),
            ('120', '87ff87'),
            ('121', '87ffaf'),
            ('122', '87ffd7'),
            ('123', '87ffff'),
            ('124', 'af0000'),
            ('125', 'af005f'),
            ('126', 'af0087'),
            ('127', 'af00af'),
            ('128', 'af00d7'),
            ('129', 'af00ff'),
            ('130', 'af5f00'),
            ('131', 'af5f5f'),
            ('132', 'af5f87'),
            ('133', 'af5faf'),
            ('134', 'af5fd7'),
            ('135', 'af5fff'),
            ('136', 'af8700'),
            ('137', 'af875f'),
            ('138', 'af8787'),
            ('139', 'af87af'),
            ('140', 'af87d7'),
            ('141', 'af87ff'),
            ('142', 'afaf00'),
            ('143', 'afaf5f'),
            ('144', 'afaf87'),
            ('145', 'afafaf'),
            ('146', 'afafd7'),
            ('147', 'afafff'),
            ('148', 'afd700'),
            ('149', 'afd75f'),
            ('150', 'afd787'),
            ('151', 'afd7af'),
            ('152', 'afd7d7'),
            ('153', 'afd7ff'),
            ('154', 'afff00'),
            ('155', 'afff5f'),
            ('156', 'afff87'),
            ('157', 'afffaf'),
            ('158', 'afffd7'),
            ('159', 'afffff'),
            ('160', 'd70000'),
            ('161', 'd7005f'),
            ('162', 'd70087'),
            ('163', 'd700af'),
            ('164', 'd700d7'),
            ('165', 'd700ff'),
            ('166', 'd75f00'),
            ('167', 'd75f5f'),
            ('168', 'd75f87'),
            ('169', 'd75faf'),
            ('170', 'd75fd7'),
            ('171', 'd75fff'),
            ('172', 'd78700'),
            ('173', 'd7875f'),
            ('174', 'd78787'),
            ('175', 'd787af'),
            ('176', 'd787d7'),
            ('177', 'd787ff'),
            ('178', 'd7af00'),
            ('179', 'd7af5f'),
            ('180', 'd7af87'),
            ('181', 'd7afaf'),
            ('182', 'd7afd7'),
            ('183', 'd7afff'),
            ('184', 'd7d700'),
            ('185', 'd7d75f'),
            ('186', 'd7d787'),
            ('187', 'd7d7af'),
            ('188', 'd7d7d7'),
            ('189', 'd7d7ff'),
            ('190', 'd7ff00'),
            ('191', 'd7ff5f'),
            ('192', 'd7ff87'),
            ('193', 'd7ffaf'),
            ('194', 'd7ffd7'),
            ('195', 'd7ffff'),
            ('196', 'ff0000'),
            ('197', 'ff005f'),
            ('198', 'ff0087'),
            ('199', 'ff00af'),
            ('200', 'ff00d7'),
            ('201', 'ff00ff'),
            ('202', 'ff5f00'),
            ('203', 'ff5f5f'),
            ('204', 'ff5f87'),
            ('205', 'ff5faf'),
            ('206', 'ff5fd7'),
            ('207', 'ff5fff'),
            ('208', 'ff8700'),
            ('209', 'ff875f'),
            ('210', 'ff8787'),
            ('211', 'ff87af'),
            ('212', 'ff87d7'),
            ('213', 'ff87ff'),
            ('214', 'ffaf00'),
            ('215', 'ffaf5f'),
            ('216', 'ffaf87'),
            ('217', 'ffafaf'),
            ('218', 'ffafd7'),
            ('219', 'ffafff'),
            ('220', 'ffd700'),
            ('221', 'ffd75f'),
            ('222', 'ffd787'),
            ('223', 'ffd7af'),
            ('224', 'ffd7d7'),
            ('225', 'ffd7ff'),
            ('226', 'ffff00'),
            ('227', 'ffff5f'),
            ('228', 'ffff87'),
            ('229', 'ffffaf'),
            ('230', 'ffffd7'),
            ('231', 'ffffff'),

            # Gray-scale range.
            ('232', '080808'),
            ('233', '121212'),
            ('234', '1c1c1c'),
            ('235', '262626'),
            ('236', '303030'),
            ('237', '3a3a3a'),
            ('238', '444444'),
            ('239', '4e4e4e'),
            ('240', '585858'),
            ('241', '626262'),
            ('242', '6c6c6c'),
            ('243', '767676'),
            ('244', '808080'),
            ('245', '8a8a8a'),
            ('246', '949494'),
            ('247', '9e9e9e'),
            ('248', 'a8a8a8'),
            ('249', 'b2b2b2'),
            ('250', 'bcbcbc'),
            ('251', 'c6c6c6'),
            ('252', 'd0d0d0'),
            ('253', 'dadada'),
            ('254', 'e4e4e4'),
            ('255', 'eeeeee'),
        ]

        # Table where offset is ANSI number referring to tuple of RGB integers.
        self.ansi_rgb = tuple(
            (int(h, 16) & 255,
             (int(h, 16) >> 8) & 255,
             (int(h, 16) >> 16) & 255)
            for i, h in self.ansi_hex
        )

        self.simplify_fg = (
            ANSI_BLACK,
            ANSI_RED,
            ANSI_GREEN,
            ANSI_YELLOW,
            ANSI_BLUE,
            ANSI_MAGENTA,
            ANSI_CYAN,
            ANSI_WHITE,
            ANSI_HILITE + ANSI_BLACK,
            ANSI_HILITE + ANSI_RED,
            ANSI_HILITE + ANSI_GREEN,
            ANSI_HILITE + ANSI_YELLOW,
            ANSI_HILITE + ANSI_BLUE,
            ANSI_HILITE + ANSI_MAGENTA,
            ANSI_HILITE + ANSI_CYAN,
            ANSI_HILITE + ANSI_WHITE
        )

        self.simplify_bg = (
            ANSI_BACK_BLACK,
            ANSI_BACK_RED,
            ANSI_BACK_GREEN,
            ANSI_BACK_YELLOW,
            ANSI_BACK_BLUE,
            ANSI_BACK_MAGENTA,
            ANSI_BACK_CYAN,
            ANSI_BACK_WHITE,
            # Repeat, because we don't have hilite backgrounds.
            ANSI_BACK_BLACK,
            ANSI_BACK_RED,
            ANSI_BACK_GREEN,
            ANSI_BACK_YELLOW,
            ANSI_BACK_BLUE,
            ANSI_BACK_MAGENTA,
            ANSI_BACK_CYAN,
            ANSI_BACK_WHITE
        )

        # Generated lookup table to ANSI256 to ANSI16 simplification.
        self.ansi256_to_ansi16 = tuple(
            self._simplify_xterm256(i) for i in xrange(len(self.ansi_rgb))
        )

    def token_to_state(self, token):
        """
        Given an extended token in format '{[_]<color>', parses components.
        :rtype: ANSIState
        """
        m = self.parse_token_regex.match(token)
        if m:
            state = m.groupdict()
            return ANSIState(bg=state['bg'], fg=state['fg'],
                             special=state['special'])
        else:
            raise ValueError("Invalid ANSI token: %s" % token)

    def state_to_tokens(self, state):
        code = ''
        if state.bg is not None:
            code += '{_' + state.bg
        if state.fg is not None:
            code += '{' + state.fg
        if state.special is not None:
            code += '{' + state.special
        return code

    def final_state(self, text):
        """
        Determine the effective final ANSI state given an ANSI string with ANSI
        tokens (ie: not converted into sequences!).
        :rtype: ANSIState
        """
        normal = self.token_to_state('{n')
        state = normal
        for token in self._token_regex.findall(text):
            if token == '{n':
                state = normal
            else:
                state = state.update(self.token_to_state(token))
        return state

    def _simplify_xterm256(self, colornum):
        """
        Low-level function to simplify an xterm256 color integer into the
        ANSI256 integer for the corresponding ANSI16 color (0-15).
        """
        tbl = self.ansi_rgb
        red, green, blue = tbl[colornum]
        smallest_distance = 10000000000.0
        best_match = 0
        for c in xrange(16):
            cr, cg, cb = tbl[c]
            d = pow(cr - red, 2) + pow(cg - green, 2) + pow(cb - blue, 2)
            if d < smallest_distance:
                smallest_distance = d
                best_match = c
        return best_match

    def parse_xterm256(self, colornum):
        bg = False
        if not isinstance(colornum, int):
            if not colornum:
                return ''
            if not isinstance(colornum, str):
                colornum = colornum.groups()[0]
            bg = colornum.startswith('_')
            colornum = int(colornum[1 if bg else 0:])
        return ANSI_ESCAPE + ('[%d;5;%dm' % (48 if bg else 38, colornum))

    def xterm256_as_ansi16(self, match):
        """
        Regex replacement callback to replace an xterm256 token with its
        best ANSI16 match.
        """
        if not match:
            return ''
        input = match.groups()[0]
        if not input:
            return ''
        background = input.startswith('_')
        xterm256num = int(input[1 if background else 0:])
        codes = self.simplify_bg if background else self.simplify_fg
        return codes[self.ansi256_to_ansi16[xterm256num]]

    def parse_rgb(self, rgbmatch):
        """
        This is a replacer method called by re.sub with the matched
        tag. It must return the correct ansi sequence.

        It checks self.do_xterm256 to determine if conversion
        to standard ansi should be done or not.
        """
        if not rgbmatch:
            return ""
        rgbtag = rgbmatch.groups()[0]

        background = rgbtag[0] == '_'
        if background:
            red, green, blue = int(rgbtag[1]), int(rgbtag[2]), int(rgbtag[3])
        else:
            red, green, blue = int(rgbtag[0]), int(rgbtag[1]), int(rgbtag[2])

        if self.do_xterm256:
            colval = 16 + (red * 36) + (green * 6) + blue
            #print "RGB colours:", red, green, blue
            return ("\033[%s8;5;%s%s%sm" %
                    (3 + int(background),
                     colval / 100,
                     (colval % 100) / 10,
                     colval % 10))
        else:
            #print "ANSI convert:", red, green, blue
            # xterm256 not supported, convert the rgb value to ansi instead
            if red == green and red == blue and red < 2:
                if background:
                    return ANSI_BACK_BLACK
                elif red >= 1:
                    return ANSI_HILITE + ANSI_BLACK
                else:
                    return ANSI_NORMAL + ANSI_BLACK
            elif red == green and red == blue:
                if background:
                    return ANSI_BACK_WHITE
                elif red >= 4:
                    return ANSI_HILITE + ANSI_WHITE
                else:
                    return ANSI_NORMAL + ANSI_WHITE
            elif red > green and red > blue:
                if background:
                    return ANSI_BACK_RED
                elif red >= 3:
                    return ANSI_HILITE + ANSI_RED
                else:
                    return ANSI_NORMAL + ANSI_RED
            elif red == green and red > blue:
                if background:
                    return ANSI_BACK_YELLOW
                elif red >= 3:
                    return ANSI_HILITE + ANSI_YELLOW
                else:
                    return ANSI_NORMAL + ANSI_YELLOW
            elif red == blue and red > green:
                if background:
                    return ANSI_BACK_MAGENTA
                elif red >= 3:
                    return ANSI_HILITE + ANSI_MAGENTA
                else:
                    return ANSI_NORMAL + ANSI_MAGENTA
            elif green > blue:
                if background:
                    return ANSI_BACK_GREEN
                elif green >= 3:
                    return ANSI_HILITE + ANSI_GREEN
                else:
                    return ANSI_NORMAL + ANSI_GREEN
            elif green == blue:
                if background:
                    return ANSI_BACK_CYAN
                elif green >= 3:
                    return ANSI_HILITE + ANSI_CYAN
                else:
                    return ANSI_NORMAL + ANSI_CYAN
            else:    # mostly blue
                if background:
                    return ANSI_BACK_BLUE
                elif blue >= 3:
                    return ANSI_HILITE + ANSI_BLUE
                else:
                    return ANSI_NORMAL + ANSI_BLUE

    def parse_ansi(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.

        """
        if not string:
            return ''
        self.do_xterm256 = xterm256

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            for sub in self.ansi_sub:
                part = sub[0].sub(sub[1], part)
            string += "%s%s" % (part, sep[0].strip())
        if strip_ansi:
            # remove all ansi codes (including those manually inserted)
            string = self.ansi_regex.sub("", string)
        return string

    # Slightly more efficient version.
    def parse_ansi2(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.
        """
        if not string:
            return ''
        self.do_xterm256 = xterm256

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            for sub in self.xterm256_sub:
                part = sub[0].sub(sub[1], part)
            for sub in self.ansi_map:
                part = part.replace(sub[0], sub[1])
            string += "%s%s" % (part, sep[0].strip())

        if strip_ansi:
            # remove all ansi codes (including those manually inserted)
            string = self.ansi_regex.sub("", string)

        return string

    # Efficient, handles xterm256 properly.
    def parse_ansi3(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.
        """
        if not string:
            return ''
        xterm256_regex = self.xterm256_regex
        xterm256_replace = (self.parse_xterm256 if xterm256
                            else self.xterm256_as_ansi16)

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            part = xterm256_regex.sub(xterm256_replace, part)
            for sub in self.ansi_map:
                part = part.replace(sub[0], sub[1])
            string += "%s%s" % (part, sep[0].strip())

        if strip_ansi:
            # remove all ansi codes (including those manually inserted)
            string = self.ansi_regex.sub("", string)

        return string

    def strip_ansi(self, string):
        """
        Strips ANSI tokens and any raw ANSI codes.
        """
        return self.ansi_regex.sub('', self._token_regex.sub('', string))

    def strip_tokens(self, string):
        """
        Strips only ANSI tokens, and will leave raw ANSI codes in place.
        """
        return self._token_regex.sub('', string)

    def escape_tokens(self, string):
        """
        Escape ANSI tokens, but leaves raw ANSI codes alone.
        """
        return self.token_regex.sub(r'{\1', string)

    def length(self, string):
        """
        Returns the integer length of the string without any ANSI tokens or
        raw sequences.
        """
        return len(self.strip_ansi(string))

    def slice(self, string, start=None, end=None):
        if start is None and end is None:
            return string
        parts = []
        stash = ''
        for i, s in enumerate(self.compound_regex.split(string)):
            if i % 2 == 1:  # Odd, so it's an ANSI token or code.
                stash += s
            else:  # Normal part of the string.
                chars = list(s)
                if stash and chars:
                    chars[0] = '%s%s' % (stash, chars[0])
                    stash = ''
                parts.extend(chars)
        out = parts[start:end]
        return stash + ''.join(out)


ANSI_PARSER = ANSIParser()


class AnsiWrapper(textwrap.TextWrapper):
    ansi_parser = ANSI_PARSER

    def _wrap_chunks(self, chunks):
        length = self.ansi_parser.length

        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - length(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                l = length(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and length(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            # If the last chunk on this line is all whitespace, drop it.
            if (self.drop_whitespace and cur_line
                    and cur_line[-1].strip() == ''):
                del cur_line[-1]

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                lines.append(indent + ''.join(cur_line))

        # Preserve ANSI state across lines.
        ansi_state = ''
        for i, line in enumerate(lines):
            line = ansi_state + line
            lines[i] = line
            ansi_state = self.ansi_parser.state_to_tokens(
                self.ansi_parser.final_state(line))

        return lines


def _parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER, xterm256=False):
    """
    Parses a string, subbing color codes as needed.
    """
    return parser.parse_ansi(string, strip_ansi=strip_ansi, xterm256=xterm256)


def parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER, xterm256=False):
    """
    Parses a string, subbing color codes as needed.
    @rtype: str
    """
    return parser.parse_ansi3(string, strip_ansi=strip_ansi, xterm256=xterm256)


def strip_ansi(string, parser=ANSI_PARSER):
    """
    Removes ANSI tokens and raw ANSI codes.
    @rtype: str
    """
    return parser.strip_ansi(string)


def escape_ansi_tokens(string, parser=ANSI_PARSER):
    """
    @rtype: str
    """
    return parser.escape_tokens(string)


def strip_ansi_tokens(string, parser=ANSI_PARSER):
    """
    @rtype: str
    """
    return parser.strip_tokens(string)


def length(string, parser=ANSI_PARSER):
    """
    Return the integer length of the string. Excludes ANSI codes.
    """
    return parser.length(string)


def slice(string, start=None, end=None, parser=ANSI_PARSER):
    return parser.slice(string, start, end)


def _str_passthru(func, string, parser, *args, **kwargs):
    """
    @rtype: str
    """
    _s = parser.strip_ansi(string)
    s = func(_s, *args, **kwargs)
    return s.replace(_s, string)


def center(string, width, fillchar=' ', parser=ANSI_PARSER):
    """
    ANSI-aware centering.
    @rtype: str
    """
    return _str_passthru(str.center, string, parser, width, fillchar)


def ljust(string, width, fillchar=' ', parser=ANSI_PARSER):
    """
    ANSI-aware ljust.
    @rtype: str
    """
    return _str_passthru(str.ljust, string, parser, width, fillchar)


def rjust(string, width, fillchar=' ', parser=ANSI_PARSER):
    """
    ANSI-aware rjust.
    @rtype: str
    """
    return _str_passthru(str.rjust, string, parser, width, fillchar)


def endswith(string, suffix, start=None, end=None, parser=ANSI_PARSER):
    """
    ANSI-aware endswith.
    @rtype: bool
    """
    return parser.strip(string).endswith(suffix, start, end)


def startswith(string, prefix, start=None, end=None, parser=ANSI_PARSER):
    """
    ANSI-aware startswith.
    @rtype: bool
    """
    return parser.strip(string).startswith(prefix, start, end)


def wrap(text, width=78, **kwargs):
    """
    ANSI-aware line wrapping for single paragraph in 'text'.

    Implements same API as textwrap.wrap().

    @rtype: list
    """
    wrapper = AnsiWrapper(width=width, **kwargs)
    return wrapper.wrap(text)


def fill(text, width=78, **kwargs):
    """
    ANSI-aware line wrapping for single paragraph in 'text' to single string
    containing line breaks.

    Implements same API as textwrap.fill().

    @rtype: str
    """
    wrapper = AnsiWrapper(width=width, **kwargs)
    return wrapper.fill(text)


def linewrap(text, width=78, linebreaks=True, **kwargs):
    """
    ANSI-aware wrapping. Considers each line in text to be a separate
    paragraph to be wrapped independently of the other lines. This effectively
    preserves existing linebreaks while introducing new ones to keep keep line
    length within the specified width.

    Implements same API as textwrap.wrap().

    @param linebreaks: Whether to return text with linebreaks or a list.
    @return: A list of string lines.
    @rtype: list
    """
    w = AnsiWrapper(width=width, **kwargs)
    paragraphs = [w.wrap(p) for p in text.splitlines()]
    lines = reduce(operator.iadd, paragraphs)
    return lines if not linebreaks else '\n'.join(lines)
