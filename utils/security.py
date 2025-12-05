import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    return private_key, public_key

def get_public_key(public_key):
    return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

def get_private_key(private_key):
    return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    
def encrypt_message(message: bytes, public_key: bytes) -> bytes:
    public_key = serialization.load_pem_public_key(public_key)
    
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(message) + encryptor.finalize()
    
    encrypted_key = public_key.encrypt(
    aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return {
        "ciphertext": ciphertext,
        "encrypted_key": encrypted_key,
        "iv": iv
    }

def decrypt_message(encrypted_block: dict, private_key: bytes) -> dict:
    private_key = serialization.load_pem_private_key(private_key, password=None)

    aes_key = private_key.decrypt(
    encrypted_block['encrypted_key'],
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(encrypted_block["iv"]))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(encrypted_block["ciphertext"]) + decryptor.finalize()
    
    return plaintext