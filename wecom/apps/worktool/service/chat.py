import json
import os.path

from openai import OpenAI

from config import settings
from wecom.utils.log import logger
from wecom.core.expired_dict import ExpiredDict
from wecom.bot.chatgpt_session import num_tokens_from_messages


class ChatCompletion:
    SESSIONS = ExpiredDict(settings.SESSION_EXPIRES_IN_SECONDS)

    def __init__(self, session_id, query):
        self.session_id = session_id
        self.sessions = self.SESSIONS

        self.model = "gpt-4o"
        self.max_tokens = 80000
        self.client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_API_BASE"],
        )

        self._add_query(query)

    def _add_query(self, query):
        if self.session_id not in self.sessions:
            self.sessions[self.session_id] = [dict(role="system", content=os.environ["DEFAULT_SYSTEM_PROMPT"])]

        user_item = {"role": "user", "content": query}
        self.sessions[self.session_id].append(user_item)

        try:
            total_tokens = self._discard_threshold(self.max_tokens, None)
            logger.info("ChatCompletion => prompt tokens used=%s", total_tokens)
        except Exception as e:
            logger.error("ChatCompletion => error when counting tokens precisely for prompt:%s}", e)

    def _add_reply(self, reply, total_tokens=None):
        assistant_item = {"role": "assistant", "content": reply}
        self.sessions[self.session_id].append(assistant_item)

        try:
            tokens_cnt = self._discard_threshold(self.max_tokens, total_tokens)
            logger.debug("ChatCompletion => raw total_tokens=%s, save session tokens=%s", total_tokens, tokens_cnt)
        except Exception as e:
            logger.warning("ChatCompletion => Exception when counting tokens precisely for session: %s", e)

    def _clear_session(self):
        self.sessions[self.session_id].clear()

    def _discard_threshold(self, max_tokens, cur_tokens=None):
        precise = True
        messages = self.sessions[self.session_id]

        try:
            cur_tokens = self._calc_tokens()
        except Exception as e:
            precise = False
            if cur_tokens is None:
                raise e
            logger.info("ChatCompletion => error when counting tokens precisely for query: %s", e)

        while cur_tokens > max_tokens:
            if len(messages) > 2:
                messages.pop(1)
            elif len(messages) == 2 and messages[1]["role"] == "assistant":
                messages.pop(1)

                if precise:
                    cur_tokens = self._calc_tokens()
                else:
                    cur_tokens = cur_tokens - max_tokens
                break

            elif len(messages) == 2 and messages[1]["role"] == "user":
                logger.warn("ChatCompletion => user message exceed max_tokens. total_tokens=%s", cur_tokens)
                break
            else:
                logger.info("ChatCompletion => max_tokens=%s, total_tokens=%s, len(messages)=%s", max_tokens, cur_tokens, len(messages))
                break
            if precise:
                cur_tokens = self._calc_tokens()
            else:
                cur_tokens = cur_tokens - max_tokens

        return cur_tokens

    def _calc_tokens(self):
        messages = self.sessions[self.session_id]
        return num_tokens_from_messages(messages, self.model)

    def stream_generator(self):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.sessions[self.session_id],
            temperature=0.9,
            max_tokens=4096,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=True
        )
        for chunk in response:
            logger.info("stream chunk: %s", chunk.dict())
            sse_message = f"data: {json.dumps(chunk.dict())}\n\n"
            yield sse_message
