from flaskr.core.security import hash_password, verify_password


class TestSecurity:
    def test_hash_is_not_plain_password(self):
        assert hash_password("secret1") != "secret1"

    def test_same_password_gets_different_hashes(self):
        # random salt per hash
        assert hash_password("secret1") != hash_password("secret1")

    def test_verify_correct_password(self):
        assert verify_password(hash_password("secret1"), "secret1") is True

    def test_verify_wrong_password(self):
        assert verify_password(hash_password("secret1"), "secret2") is False
