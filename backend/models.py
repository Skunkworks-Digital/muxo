"""SQLAlchemy models for core application data."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    msisdn = Column(String, unique=True, nullable=False)
    name = Column(String)
    opt_out = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lists = relationship("ListMember", back_populates="contact")
    messages = relationship("Message", back_populates="contact")


class List(Base):
    __tablename__ = "lists"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    members = relationship("ListMember", back_populates="list")


class ListMember(Base):
    __tablename__ = "list_members"

    list_id = Column(Integer, ForeignKey("lists.id"), primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    list = relationship("List", back_populates="members")
    contact = relationship("Contact", back_populates="lists")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    list_id = Column(Integer, ForeignKey("lists.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    window_start = Column(String)
    window_end = Column(String)
    rate_limit = Column(Integer, nullable=False, default=1)

    messages = relationship("Message", back_populates="campaign")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    port = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    messages = relationship("Message", back_populates="device")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    text = Column(Text, nullable=False)
    ref = Column(String)
    status = Column(String, default="queued", nullable=False)
    error_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    campaign = relationship("Campaign", back_populates="messages")
    contact = relationship("Contact", back_populates="messages")
    device = relationship("Device", back_populates="messages")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True)
    keyword = Column(String, nullable=False)
    response = Column(Text, nullable=False)


class Audit(Base):
    __tablename__ = "audit"

    id = Column(Integer, primary_key=True)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

