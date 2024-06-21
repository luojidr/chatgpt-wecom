from wecom.utils.log import logger
from ..core.expired_dict import ExpiredDict
from config import settings, prompts


class Session:
    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        self.messages = []

        if system_prompt is None:
            self.system_prompt = settings.DEFAULT_OPENAI_SYSTEM_PROMPT
        else:
            self.system_prompt = system_prompt

    # 重置会话
    def reset(self):
        system_item = {"role": "system", "content": self.system_prompt}
        self.messages = [system_item]

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        self.reset()

    def add_query(self, query):
        user_item = {"role": "user", "content": query}
        self.messages.append(user_item)

    def add_reply(self, reply):
        assistant_item = {"role": "assistant", "content": reply}
        self.messages.append(assistant_item)

    def discard_exceeding(self, max_tokens, cur_tokens=None):
        raise NotImplementedError

    def calc_tokens(self):
        raise NotImplementedError


class SessionManager:
    def __init__(self, session_cls, **session_kwargs):
        if settings.SESSION_EXPIRES_IN_SECONDS:
            sessions = ExpiredDict(settings.SESSION_EXPIRES_IN_SECONDS)
        else:
            sessions = dict()
        self.sessions = sessions
        self.session_cls = session_cls
        self.session_kwargs = session_kwargs
        self.max_tokens = settings.CONVERSATION_MAX_TOKENS or 10000

    def build_session(self, session_id, system_prompt=None):
        """
        如果session_id不在sessions中，创建一个新的session并添加到sessions中
        如果system_prompt不会空，会更新session的system_prompt并重置session
        """
        if session_id is None:
            return self.session_cls(session_id, system_prompt, **self.session_kwargs)

        if session_id not in self.sessions:
            if system_prompt:
                self.session_kwargs.setdefault("system_prompt", system_prompt)

            self.sessions[session_id] = self.session_cls(session_id, **self.session_kwargs)
        elif system_prompt is not None:  # 如果有新的system_prompt，更新并重置session
            self.sessions[session_id].set_system_prompt(system_prompt)
        session = self.sessions[session_id]
        return session

    def session_query(self, query, session_id):
        session = self.build_session(session_id)
        session.add_query(query)

        try:
            total_tokens = session.discard_exceeding(self.max_tokens, None)
            logger.debug("prompt tokens used={}".format(total_tokens))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for prompt: {}".format(str(e)))
        return session

    def session_reply(self, reply, session_id, total_tokens=None):
        session = self.build_session(session_id)
        session.add_reply(reply)

        try:
            tokens_cnt = session.discard_exceeding(self.max_tokens, total_tokens)
            logger.debug("raw total_tokens={}, savesession tokens={}".format(total_tokens, tokens_cnt))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for session: {}".format(str(e)))
        return session

    def clear_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all_session(self):
        self.sessions.clear()


class GroupSessionManager:
    def __init__(self, session_cls, **session_kwargs):
        self.g_sessions = {}

        # 所有的聊天组使用相同的Session
        self.session_cls = session_cls
        self.session_kwargs = session_kwargs

    def _get_session(self, group_name, system_prompt=None):
        if system_prompt is None:
            system_prompt = prompts.WT_GROUP_PROMPTS[group_name]

        if group_name not in self.g_sessions:
            self.g_sessions[group_name] = SessionManager(
                self.session_cls,
                system_prompt=system_prompt,
                **self.session_kwargs
            )

        return self.g_sessions[group_name]

    def add_query(self, group_name, query, session_id):
        g_session = self._get_session(group_name)
        return g_session.session_query(query, session_id)

    def add_reply(self, group_name, reply, session_id, total_tokens=None):
        g_session = self._get_session(group_name)
        return g_session.session_reply(reply, session_id, total_tokens)




