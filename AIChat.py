
from typing import List, Dict
from numbers import Number
import openai

class AIChat:
    def __init__(
                self,
                messages:List[Dict[str, str]] = [],
                conversation_id: str = "",
                qq: str = "",
                group_id: str = "",
                model: str = "gpt-3.5-turbo", # "gpt-3.5-turbo" or "gpt-3.5-turbo-0301"
                temperature: Number = 1, # between 0 and 2
                max_tokens: int = 100, # not recommend but max = 4096
                presence_penalty: Number = 0, # between -2.0 and 2.0
                frequency_penalty: Number = 0 # between -2.0 and 2.0
    ):
        self.messages = messages
        self.conversation_id = conversation_id
        self.qq = qq
        self.group_id = group_id
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty

        self.full_token_cost = 0
        self.last_token_cost = 0

    def add_conversation_msg(self, role: str, content: str):
        message = {"role": role, "content": content}
        self.messages.append(message)

    def get_full_response(self):
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,# Defaults to 1. between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.
            max_tokens=self.max_tokens, # default 4096 or inf. maximum number of tokens allowed for the generated answer. 
            presence_penalty=self.presence_penalty, #default 0. between -2.0 and 2.0, increasing the model's likelihood to talk about new topics
            frequency_penalty=self.frequency_penalty #default 0. between -2.0 and 2.0, decreasing the model's likelihood to repeat the same line verbatim.
        )
        return response
    
    def get_reply(self, msg: str):
        self.add_conversation_msg("user", msg)
        try:
            response = self.get_full_response()
            reply = response["choices"][0]["message"]["content"]
            self.add_conversation_msg("assistant", msg)
            token_cost = response["usage"]["total_tokens"]
            self.last_token_cost = token_cost
            self.full_token_cost += token_cost
            return reply
        except openai.error.OpenAIError as e:
            return e._message

    def add_conversation_setting(self, msg: str):
        self.add_conversation_msg("system", msg)

    def clear_all(self):
        self.messages = []
        self.full_token_cost = 0
        self.last_token_cost = 0

    def clear_messages(self):
        new_messages = []
        self.full_token_cost = 0
        self.last_token_cost = 0
        for message in self.messages:
            if message["role"] == "system":
                new_messages.append(message)
        self.messages = new_messages

    def get_full_token_cost(self):
        return self.full_token_cost

    def get_last_token_cost(self):
        return self.last_token_cost

    def get_conversation_id(self):
        return self.conversation_id

    def to_dict(self):
        output = {
            "messages": self.messages,
            "conversation_id": self.conversation_id,
            "qq": self.qq,
            "group_id": self.group_id,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "full_token_cost": self.full_token_cost,
            "last_token_cost": self.last_token_cost
        }
        return output

    def load_dict(self, conversation: dict):
        self.messages = conversation["messages"]
        self.conversation_id = conversation["conversation_id"]
        self.qq = conversation["qq"]
        self.group_id = conversation["group_id"]
        self.model = conversation["model"]
        self.temperature = conversation["temperature"]
        self.max_tokens = conversation["max_tokens"]
        self.presence_penalty = conversation["presence_penalty"]
        self.frequency_penalty = conversation["frequency_penalty"]
        self.full_token_cost = conversation["full_token_cost"]
        self.last_token_cost = conversation["last_token_cost"]