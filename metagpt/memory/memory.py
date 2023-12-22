#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/20 12:15
@Author  : alexanderwu
@File    : memory.py
@Modified By: mashenquan, 2023-11-1. According to RFC 116: Updated the type of index key.
"""
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Set

from pydantic import BaseModel, Field

from metagpt.schema import Message
from metagpt.utils.common import (
    any_to_str,
    any_to_str_set,
    read_json_file,
    write_json_file,
)


class Memory(BaseModel):
    """The most basic memory: super-memory"""

    storage: list[Message] = []
    index: dict[str, list[Message]] = Field(default_factory=defaultdict(list))

    def __init__(self, **kwargs):
        index = kwargs.get("index", {})
        new_index = defaultdict(list)
        for action_str, value in index.items():
            new_index[action_str] = [Message(**item_dict) for item_dict in value]
        kwargs["index"] = new_index
        super(Memory, self).__init__(**kwargs)
        self.index = new_index

    def serialize(self, stg_path: Path):
        """stg_path = ./storage/team/environment/ or ./storage/team/environment/roles/{role_class}_{role_name}/"""
        memory_path = stg_path.joinpath("memory.json")
        storage = self.dict()
        write_json_file(memory_path, storage)

    @classmethod
    def deserialize(cls, stg_path: Path) -> "Memory":
        """stg_path = ./storage/team/environment/ or ./storage/team/environment/roles/{role_class}_{role_name}/"""
        memory_path = stg_path.joinpath("memory.json")

        memory_dict = read_json_file(memory_path)
        memory = Memory(**memory_dict)

        return memory

    def add(self, message: Message):
        """Add a new message to storage, while updating the index"""
        if message in self.storage:
            return
        self.storage.append(message)
        if message.cause_by:
            self.index[message.cause_by].append(message)

    def add_batch(self, messages: Iterable[Message]):
        for message in messages:
            self.add(message)

    def get_by_role(self, role: str) -> list[Message]:
        """Return all messages of a specified role"""
        return [message for message in self.storage if message.role == role]

    def get_by_content(self, content: str) -> list[Message]:
        """Return all messages containing a specified content"""
        return [message for message in self.storage if content in message.content]

    def delete_newest(self) -> "Message":
        """delete the newest message from the storage"""
        if len(self.storage) > 0:
            newest_msg = self.storage.pop()
            if newest_msg.cause_by and newest_msg in self.index[newest_msg.cause_by]:
                self.index[newest_msg.cause_by].remove(newest_msg)
        else:
            newest_msg = None
        return newest_msg

    def delete(self, message: Message):
        """Delete the specified message from storage, while updating the index"""
        self.storage.remove(message)
        if message.cause_by and message in self.index[message.cause_by]:
            self.index[message.cause_by].remove(message)

    def clear(self):
        """Clear storage and index"""
        self.storage = []
        self.index = defaultdict(list)

    def count(self) -> int:
        """Return the number of messages in storage"""
        return len(self.storage)

    def try_remember(self, keyword: str) -> list[Message]:
        """Try to recall all messages containing a specified keyword"""
        return [message for message in self.storage if keyword in message.content]

    def get(self, k=0) -> list[Message]:
        """Return the most recent k memories, return all when k=0"""
        return self.storage[-k:]

    def find_news(self, observed: list[Message], k=0) -> list[Message]:
        """find news (previously unseen messages) from the the most recent k memories, from all memories when k=0"""
        already_observed = self.get(k)
        news: list[Message] = []
        for i in observed:
            if i in already_observed:
                continue
            news.append(i)
        return news

    def get_by_action(self, action) -> list[Message]:
        """Return all messages triggered by a specified Action"""
        index = any_to_str(action)
        return self.index[index]

    def get_by_actions(self, actions: Set) -> list[Message]:
        """Return all messages triggered by specified Actions"""
        rsp = []
        indices = any_to_str_set(actions)
        for action in indices:
            if action not in self.index:
                continue
            rsp += self.index[action]
        return rsp

    def get_by_tags(self, tags: list) -> list[Message]:
        """Return messages with specified tags"""
        result = []
        for m in self.storage:
            if m.is_contain_tags(tags):
                result.append(m)
        return result
