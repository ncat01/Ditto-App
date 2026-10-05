package com.ditto.app.core

import android.content.Context
import android.database.sqlite.SQLiteOpenHelper
import android.database.sqlite.SQLiteDatabase
import android.content.ContentValues
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import java.security.SecureRandom
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec

/** Offline accounts are device-local. No server login or email delivery is implied. */
class LocalAccounts(private val context: Context) : SQLiteOpenHelper(context, "accounts.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE accounts(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, password BLOB NOT NULL)")
    }
    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) = Unit
    private val preferences = context.getSharedPreferences("secure_session", Context.MODE_PRIVATE)
    private fun hash(password: String, salt: ByteArray) = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        .generateSecret(PBEKeySpec(password.toCharArray(), salt, 210000, 256)).encoded
    fun signup(email: String, password: String): String {
        require(android.util.Patterns.EMAIL_ADDRESS.matcher(email.trim()).matches()) { "Enter a valid email address." }
        require(password.length in 10..128) { "Use a password of 10 to 128 characters." }
        val salt = ByteArray(32).also { SecureRandom().nextBytes(it) }
        val id = UUID.randomUUID().toString()
        val values = ContentValues().apply {
            put("id", id); put("email", email.trim().lowercase()); put("salt", salt); put("password", hash(password, salt))
        }
        require(writableDatabase.insert("accounts", null, values) != -1L) { "That account already exists on this device." }
        saveSession(id)
        return id
    }
    fun login(email: String, password: String): String {
        require(password.length <= 128) { "Password is too long." }
        readableDatabase.rawQuery("SELECT id,salt,password FROM accounts WHERE email=?", arrayOf(email.trim().lowercase())).use {
            require(it.moveToFirst()) { "Email or password is incorrect." }
            require(java.security.MessageDigest.isEqual(hash(password,it.getBlob(1)),it.getBlob(2))) { "Email or password is incorrect." }
            val id = it.getString(0); saveSession(id); return id
        }
    }
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("ditto_session", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("ditto_session",KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    private fun saveSession(id: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE,key()) }
        val data = cipher.doFinal("$id|${System.currentTimeMillis()+7*86400000L}".toByteArray())
        preferences.edit().putString("session",Base64.encodeToString(cipher.iv+data,Base64.NO_WRAP)).commit()
    }
    fun session(): String? = runCatching {
        val bytes = Base64.decode(preferences.getString("session",null) ?: return null,Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,bytes.copyOfRange(0,12))) }
        val parts = String(cipher.doFinal(bytes.copyOfRange(12,bytes.size))).split('|')
        if (parts[1].toLong()>System.currentTimeMillis()) parts[0] else null
    }.getOrNull()
    fun logout() { preferences.edit().remove("session").commit() }
    fun saveSecret(name: String, value: String) {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE,key()) }
        preferences.edit().putString(name,Base64.encodeToString(cipher.iv+cipher.doFinal(value.toByteArray()),Base64.NO_WRAP)).commit()
    }
    fun secret(name: String): String? = runCatching {
        val bytes=Base64.decode(preferences.getString(name,null) ?: return null,Base64.NO_WRAP)
        val cipher=Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,bytes.copyOfRange(0,12))) }
        String(cipher.doFinal(bytes.copyOfRange(12,bytes.size)))
    }.getOrNull()
    fun removeSecret(name: String) { preferences.edit().remove(name).commit() }
    fun onboardingDone() = preferences.getBoolean("onboarding",false)
    fun finishOnboarding() { preferences.edit().putBoolean("onboarding",true).apply() }
}
