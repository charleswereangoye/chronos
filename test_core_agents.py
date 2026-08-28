import pytest
import os
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

from shared.base_agent import BaseAgent, AgentResult, AgentStatus
from shared.memory import MemoryManager
from agents.forex_agent.monitor import ForexMonitor
from agents.forex_agent.advisor import ForexAdvisor
from agents.daily_updates.email_agent import EmailAgent
from agents.daily_updates.phone_connector import PhoneConnector
from agents.job_seeking.job_scraper import JobScraper

class MockAgent(BaseAgent):
    async def execute(self, payload=None):
        if payload and payload.get('fail'):
            raise ValueError('Test Failure')
        return AgentResult(status=AgentStatus.SUCCESS, data={'msg': 'ok'})

@pytest.mark.asyncio
async def test_base_agent_lifecycle_success():
    agent = MockAgent()
    assert agent.status == AgentStatus.IDLE
    result = await agent.run({'fail': False})
    assert result.is_success
    assert result.data['msg'] == 'ok'
    assert agent.status == AgentStatus.SUCCESS

@pytest.mark.asyncio
async def test_base_agent_lifecycle_failure():
    agent = MockAgent()
    result = await agent.run({'fail': True})
    assert not result.is_success
    assert result.status == AgentStatus.FAILED
    assert 'Test Failure' in result.error_message
    assert agent.status == AgentStatus.FAILED

def test_memory_manager_thread_safety_and_bounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, 'history.json')
        mem = MemoryManager(history_path=tmp_file)
        
        # Save 60 items (should cap at 50)
        history = mem.load_history()
        history['quotes'] = [f'quote_{i}' for i in range(60)]
        mem.save_history(history)
        
        reloaded = mem.load_history()
        assert len(reloaded['quotes']) == 50
        assert reloaded['quotes'][-1] == 'quote_59'

@pytest.mark.asyncio
async def test_forex_monitor_sessions():
    monitor = ForexMonitor()
    result = await monitor.run()
    assert result.is_success
    assert 'London_Session' in result.data['market_sessions']

@pytest.mark.asyncio
async def test_daily_updates_phone_connector():
    connector = PhoneConnector()
    result = await connector.run({'title': 'Urgent Job', 'message': 'New application matched', 'urgency': 'HIGH'})
    assert result.is_success
    assert result.data['delivered'] is True

def test_job_scraper_filtering():
    scraper = JobScraper()
    assert scraper.is_early_career_friendly('Junior Python Developer', 'Great opportunity for beginners') is True
    assert scraper.is_early_career_friendly('Software Engineer Intern', 'Learn on the job') is True
    assert scraper.is_early_career_friendly('Senior Staff Architect', 'Requires 10+ years experience') is False
