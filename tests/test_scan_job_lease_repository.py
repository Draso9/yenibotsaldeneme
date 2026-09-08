"""Exercise the real repository against a versioned Firestore document boundary."""
from copy import deepcopy
from types import SimpleNamespace

from google.api_core.exceptions import FailedPrecondition
from izfin_repositories.signal_repository import ScanJobRepository


class Document:
    def __init__(self):
        self.data = {"job_id": "job", "owner_uid": "owner", "worker_id": "worker", "status": "running", "lease_expires_at": 100}
        self.version = 1
        self.before_update = None

    def get(self):
        data = deepcopy(self.data)
        return SimpleNamespace(exists=True, update_time=self.version, to_dict=lambda: data)

    def update(self, data, *, option):
        if self.before_update:
            self.before_update()
            self.before_update = None
        if option._last_update_time != self.version:
            raise FailedPrecondition("Changed document")
        self.data.update(data)
        self.version += 1


def repository():
    doc = Document()
    db = SimpleNamespace(collection=lambda _: SimpleNamespace(document=lambda _: doc))
    return ScanJobRepository(db), doc


def test_heartbeat_between_read_and_expiry_write_prevents_false_interruption():
    repo, doc = repository()

    def renew():
        doc.data['lease_expires_at'] = 300
        doc.version += 1

    doc.before_update = renew
    result = repo.interrupt_expired_job('job', 'owner', now=200)
    assert result['status'] == 'running'
    assert result['lease_expires_at'] == 300
    assert doc.data['status'] == 'running'


def test_interruption_between_read_and_worker_write_fences_late_result():
    repo, doc = repository()

    def expire():
        doc.data.update(status='failed', stage='interrupted')
        doc.version += 1

    doc.before_update = expire
    result = repo.save_owned_job('job', {**doc.data, 'status': 'completed'})
    assert result['status'] == 'failed'
    assert doc.data['status'] == 'failed'


def test_wrong_owner_or_fresh_lease_cannot_be_interrupted():
    repo, doc = repository()
    assert repo.interrupt_expired_job('job', 'other', now=200)['status'] == 'running'
    assert repo.interrupt_expired_job('job', 'owner', now=50)['status'] == 'running'
    assert doc.version == 1


def test_expiry_is_terminal_for_the_old_writer():
    repo, doc = repository()
    assert repo.interrupt_expired_job('job', 'owner', now=200)['status'] == 'failed'
    result = repo.save_owned_job('job', {**doc.data, 'status': 'running', 'lease_expires_at': 300})
    assert result['status'] == 'failed'
