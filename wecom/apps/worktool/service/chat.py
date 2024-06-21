import json
import os.path
from typing import List, Dict

from openai import OpenAI

from config import settings, prompts
from wecom.utils.log import logger
from wecom.core.expired_dict import ExpiredDict
from wecom.bot.chatgpt_session import num_tokens_from_messages
from wecom.apps.worktool.models.script_delivery import ScriptDelivery


class ChatCompletion:
    SESSIONS = ExpiredDict(settings.SESSION_EXPIRES_IN_SECONDS * 6)

    def __init__(self, session_id, messages):
        self.session_id = session_id
        self.sessions = self.SESSIONS

        self.model = "gpt-4o"
        self.max_tokens = 80000
        self.client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_API_BASE"],
        )

        self._tmp_messages = []
        self._add_messages(messages)

    def _add_messages(self, messages: List[Dict[str, str]]):
        if not self.sessions.get(self.session_id):
            output = ScriptDelivery.get_output_by_workflow_rid(self.session_id)
            script_delivery_obj = ScriptDelivery.get_object(rid=self.session_id)
            author = script_delivery_obj.author or ""
            work_name = script_delivery_obj.work_name or ""

            self.sessions[self.session_id] = [
                dict(role="system", content=prompts.DEFAULT_SYSTEM_PROMPT),
                dict(role="user", content=prompts.DEFAULT_USER_PROMPT.format(author=author, work_name=work_name)),
            ]

            if output:
                output_data = json.loads(output)

                # user
                input_fields = output_data["ui_design"]["inputFields"]
                input_list = ["%s: %s" % (input_item["name"], input_item["value"]) for input_item in input_fields]
                self.sessions[self.session_id].append(dict(role="system", content=", ".join(input_list)))

                # assistant
                output_nodes = output_data["ui_design"]["outputNodes"][:3]
                output_list = [output_node["data"]["template"]["text"]["value"] for output_node in output_nodes]
                self.sessions[self.session_id].append(dict(role="user", content="\n".join(output_list)))

            if len(self.sessions[self.session_id]) != 4:
                raise ValueError("未发现rid: %s 的AI评估分析", self.session_id)

        if messages and messages[0]["content"] == "起飞":
            messages.pop(0)

        self._tmp_messages.extend(self.sessions[self.session_id])
        self._tmp_messages.extend(messages)
        logger.info("ChatCompletion => session_id: %s, messages: %s", self.session_id, self._tmp_messages)
        try:
            total_tokens = self._discard_threshold(self.max_tokens, None)
            logger.info("ChatCompletion => prompt tokens used=%s", total_tokens)
        except Exception as e:
            logger.error("ChatCompletion => error when counting tokens precisely for prompt:%s}", e)

    def _discard_threshold(self, max_tokens, cur_tokens=None):
        precise = True
        messages = self._tmp_messages

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
        messages = self._tmp_messages
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
            sse_message = f"data: {json.dumps(chunk.dict())}\n\n"
            yield sse_message
