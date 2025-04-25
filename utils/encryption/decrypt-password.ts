import crypto from 'crypto';

export function decrypt(encrypted: string, iv: Uint8Array, encryptionKey: Uint8Array) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', encryptionKey, iv);
  let decrypted = decipher.update(encrypted, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}