from mudsling.objects import Object
from mudsling.messages import Messages, RenderList
import mudsling.utils.time as time_utils
from mudsling.errors import InvalidObject
from mudsling.commands import Command
from mudsling.parsers import ListMatcher, MatchObject
from mudsling.locks import all_pass


class FollowableObject(Object):
    messages = Messages({
        'follow_invite': {
            'actor': 'You invite $charlist to follow you.',
            '*': '{c$actor{n invites $charlist to follow ${actor.him_her}.'
        },
        'follow_uninvite': {
            'actor': 'You stop leading $charlist.',
            '*': '{c$actor{n stops leading $charlist.'
        }
    })
    allow_follow = {}
    followers = []

    def after_object_moved(self, moved_from, moved_to, by=None, via=None):
        super(FollowableObject, self).after_object_moved(moved_from, moved_to,
                                                         by=by, via=via)
        from mudslingcore.rooms import Exit
        if self.db.is_valid(via, Exit):
            self._beckon_followers(via)

    def _beckon_followers(self, exit):
        self._prune_followers()
        for follower in self.followers:
            follower.do_follow(exit)

    def _prune_allow_follow(self):
        if 'allow_follow' not in self.__dict__:
            self.allow_follow = {}
        remove = []
        now = time_utils.unixtime()
        for char, timestamp in self.allow_follow.iteritems():
            if now - timestamp > 120:
                remove.append(char)
        for char in remove:
            del self.allow_follow[char]
        return remove

    def _prune_followers(self):
        if 'followers' not in self.__dict__:
            self.followers = []
        prune = []
        for f in self.followers:
            if not f.isa(Follower) or f.location != self.location:
                prune.append(f)
        for f in prune:
            self._terminate_follower(f)
        return prune

    def allows_following_by(self, char):
        self._prune_allow_follow()
        return char in self.allow_follow

    def follow_invite(self, charlist):
        self._prune_allow_follow()
        newly_allowed = []
        for char in charlist:
            if char not in self.allow_follow:
                newly_allowed.append(char)
                self.allow_follow[char] = time_utils.unixtime()
        if newly_allowed:
            names = RenderList(newly_allowed, format='{g%s{n')
            self.emit_message('lead', actor=self.ref(), charlist=names)
        return newly_allowed

    def follow_uninvite(self, charlist):
        self._prune_allow_follow()
        uninvite = [c for c in charlist
                    if c in self.allow_follow or c in self.followers]
        for char in uninvite:
            if char in self.allow_follow:
                del self.allow_follow[char]
            if char in self.followers:
                self._terminate_follower(char)
        if uninvite:
            names = RenderList(uninvite, format='{g%s{n')
            self.emit_message('unlead', actor=self.ref(), charlist=names)
        return uninvite

    def gain_follower(self, char):
        self._prune_followers()
        if char not in self.followers:
            self.followers.append(char)

    def lose_follower(self, char):
        self._prune_followers()
        if char in self.followers:
            self.followers.remove(char)

    def _terminate_follower(self, follower):
        """Make something stop following this from this side"""
        if follower.isa(Follower):
            follower.stop_following(self.ref())
        else:
            self.lose_follower(follower)


class Follower(Object):
    following = None

    messages = Messages({
        'follow_ask': {
            'actor': 'You ask to follow {m$char{n.',
            'char': '{c$actor{n wants to follow you. Type "{clead $actor{n" '
                    'to let ${actor.him_her} follow you.',
            '*': '{c$actor{n wants to follow {m%char{n.'
        },
        'follow': {
            'actor': 'You start following {m$char{n.',
            '*': '{c$actor{n starts following {m$char{n.'
        },
        'unfollow': {
            'actor': 'You stop following {m$char{n.',
            '*': '{c$actor{n stops following {m$char{n.'
        }
    })

    @property
    def is_following(self):
        self._prune_following()
        return self.following is not None

    def _prune_following(self):
        before = self.following
        if self.following is not None:
            if not self.following.isa(FollowableObject):
                self.following = None
            elif self.location != self.following.location:
                self.stop_following()
        return before, self.following

    def start_following(self, char):
        if self.following == char:
            return
        if (not self.db.is_valid(char, FollowableObject)
                or self.location != char.location):
            raise InvalidObject(obj=char, msg="You can't follow that.")
        if self.is_following:
            self.stop_following()
        if not char.allows_following_by(self.ref()):
            self.emit_message('follow_ask', actor=self.ref(), char=char)
        else:
            self.following = char
            char.gain_follower(self.ref())
            self.emit_message('follow', actor=self.ref(), char=char)

    def stop_following(self, following=None):
        if following is None or self.following == following:
            following = self.following
            if self.db.is_valid(following, FollowableObject):
                following.lose_follower(self.ref())
            self.following = None
            self.emit_message('unfollow', actor=self.ref(), char=following)

    def do_follow(self, exit):
        if exit in self.context:
            exit.invoke(self.ref())


match_follower = MatchObject(cls=Follower, search_for='follower', show=True)
match_leader = MatchObject(cls=FollowableObject,
                           search_for='something to follow', show=True)
match_followers = ListMatcher(match_follower)


class LeadCmd(Command):
    """
    lead <follower>[,<follower>, ...]

    Invite one or more followers.
    """
    aliases = ('lead', 'invite-follow', 'follow-invite')
    syntax = '<followers>'
    arg_parsers = {'followers': match_followers}
    lock = all_pass

    def run(self, actor, followers):
        """
        :type actor: FollowableObject
        :type followers: list of Follower
        """
        invited = actor.follow_invite(followers)
        if not invited:
            actor.tell('{yNo new follower invites.')


class UnleadCommand(Command):
    """
    unlead <char>[,<char>, ...]

    Un-invite one or more followers.
    """
    aliases = ('unlead', 'uninvite-follow', 'follow-uninvite')
    syntax = '<followers>'
    arg_parsers = {'followers': match_followers}
    lock = all_pass

    def run(self, actor, followers):
        """
        :type actor: FollowableObject
        :type followers: list of Follower
        """
        uninvited = actor.follow_uninvite(followers)
        if not uninvited:
            actor.tell('{yNo followers uninvited.')


FollowableObject.private_commands = [LeadCmd, UnleadCommand]


class FollowCmd(Command):
    """
    follow <leader>

    Follow a leader through exits. Leader must first 'lead' you.
    """
    aliases = ('follow',)
    syntax = '<leader>'
    arg_parsers = {'leader': match_leader}
    lock = all_pass

    def run(self, actor, leader):
        """
        :type actor: Follower
        :type leader: FollowableObject
        """
        if actor.following == leader:
            actor.tell('{yYou are already following ', leader, '.')
        else:
            actor.start_following(leader)


class UnfollowCmd(Command):
    """
    unfollow

    Stop following the current leader.
    """
    aliases = ('unfollow',)
    lock = all_pass

    def run(self, actor):
        """
        :type actor: Follower
        """
        if not actor.is_following:
            raise self._err('{yYou are not following.')
        actor.stop_following()


Follower.private_commands = [FollowCmd, UnfollowCmd]
