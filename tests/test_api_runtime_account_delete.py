from izfin_api.runtime import firebase_runtime


class FirebaseAuthStub:
    def verify_id_token(self, token):
        return {"uid": token, "email": "user@example.com"}

    def revoke_refresh_tokens(self, uid):
        return uid

    def delete_user(self, uid):
        return uid


class FirestoreStub:
    pass


def test_firebase_runtime_exposes_real_account_deletion_callbacks():
    auth = FirebaseAuthStub()
    runtime = firebase_runtime(firebase_auth=auth, firestore_client=FirestoreStub())

    assert runtime["revoke_refresh_tokens"].__self__ is auth
    assert runtime["delete_user"].__self__ is auth
