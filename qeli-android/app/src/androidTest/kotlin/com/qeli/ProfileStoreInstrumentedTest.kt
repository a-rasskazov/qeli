package com.qeli

import android.content.Context
import android.util.Base64
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.security.KeyStore
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProfileStoreInstrumentedTest {
    private val context: Context = ApplicationProvider.getApplicationContext()
    private val prefsName = "profile_store_instrumented_test"
    private val keyAlias = "qeli_profile_store_instrumented_test"

    @After
    fun cleanUp() {
        context.getSharedPreferences(prefsName, Context.MODE_PRIVATE).edit().clear().commit()
        KeyStore.getInstance("AndroidKeyStore").apply {
            load(null)
            if (containsAlias(keyAlias)) deleteEntry(keyAlias)
        }
    }

    @Test
    fun profileRoundTripsWithoutPlaintextAtRest() {
        val secret = "[server]\naddress = vpn.example\npassword = never-store-this-clear"
        val store = ProfileStore.SecureStore(context, prefsName, keyAlias)

        assertEquals(true, store.edit().putString("profile", secret).commit())
        assertEquals(secret, store.getString("profile", null))

        val encoded = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)
            .getString("profile", null)!!
        assertNotEquals(secret, encoded)
        assertFalse(encoded.contains("never-store-this-clear"))
        assertEquals(
            secret,
            ProfileStore.SecureStore(context, prefsName, keyAlias)
                .getString("profile", null),
        )
    }

    @Test
    fun staleActivityCannotReplaceNewerEncryptedProfiles() {
        val first = ProfileStore.SecureStore(context, prefsName, keyAlias)
        val second = ProfileStore.SecureStore(context, prefsName, keyAlias)
        val firstVersion = first.version("profile")
        val secondVersion = second.version("profile")
        val updated = first.putStringIfVersion("profile", firstVersion, "new")
        assertThrows(IllegalStateException::class.java) {
            second.putStringIfVersion("profile", secondVersion, "stale")
        }
        assertEquals("new", second.getString("profile", null))
        first.putStringIfVersion("profile", updated, "newer")
        assertEquals("newer", second.getString("profile", null))
    }

    @Test
    fun concurrentActivitiesCannotBothCommitTheSameVersion() {
        val first = ProfileStore.SecureStore(context, prefsName, keyAlias)
        val second = ProfileStore.SecureStore(context, prefsName, keyAlias)
        val version = first.version("profile")
        val start = CountDownLatch(1)
        val successes = AtomicInteger()
        val failures = ConcurrentLinkedQueue<Throwable>()
        val workers = listOf(first to "first", second to "second").map { (store, value) ->
            thread {
                start.await()
                try {
                    store.putStringIfVersion("profile", version, value)
                    successes.incrementAndGet()
                } catch (_: ProfileStore.SecureStore.StaleVersionException) {
                    // The winner's encrypted value must survive.
                } catch (error: Throwable) {
                    failures.add(error)
                }
            }
        }
        start.countDown()
        workers.forEach { it.join(10_000); assertFalse(it.isAlive) }
        assertTrue(failures.toString(), failures.isEmpty())
        assertEquals(1, successes.get())
        assertTrue(first.getString("profile", null) in setOf("first", "second"))
    }

    @Test
    fun staleRestoreCannotReplaceAnUnreadableEntry() {
        val first = ProfileStore.SecureStore(context, prefsName, keyAlias)
        val raw = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        raw.edit().putString("profile", "invalid envelope").commit()
        val restoreVersion = first.version("profile")
        assertThrows(SecurityException::class.java) { first.getString("profile", null) }
        first.putStringIfVersion("profile", restoreVersion, "recovered")
        assertEquals("recovered", first.getString("profile", null))
        assertThrows(IllegalStateException::class.java) {
            first.putStringIfVersion("profile", restoreVersion, "stale restore")
        }
        assertEquals("recovered", first.getString("profile", null))
    }

    @Test
    fun oversizedEncodedEnvelopeIsRejectedBeforeBase64Decode() {
        val store = ProfileStore.SecureStore(context, prefsName, keyAlias)
        val raw = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        val oversized = "A".repeat(ProfileStore.MAX_BASE64_CHARS + 1)
        assertTrue(raw.edit().putString("profile", oversized).commit())

        assertThrows(SecurityException::class.java) { store.getString("profile", null) }
        assertEquals(oversized, raw.getString("profile", null))
    }

    @Test
    fun oversizedPlaintextCannotReplaceEncryptedEntry() {
        val store = ProfileStore.SecureStore(context, prefsName, keyAlias)
        assertTrue(store.edit().putString("profile", "original").commit())
        val version = store.version("profile")

        assertThrows(IllegalArgumentException::class.java) {
            store.putStringIfVersion(
                "profile",
                version,
                "x".repeat(ProfileStore.MAX_PROFILE_SET_BYTES + 1),
            )
        }
        assertEquals("original", store.getString("profile", null))
        assertEquals(version, store.version("profile"))
    }

    @Test
    fun tamperAndCiphertextRelocationAreRejected() {
        val store = ProfileStore.SecureStore(context, prefsName, keyAlias)
        assertEquals(true, store.edit().putString("profile", "secret").commit())
        val raw = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        val encoded = raw.getString("profile", null)!!

        raw.edit().putString("other", encoded).commit()
        assertThrows(SecurityException::class.java) { store.getString("other", null) }

        val bytes = Base64.decode(encoded, Base64.NO_WRAP)
        bytes[bytes.lastIndex] = (bytes.last().toInt() xor 1).toByte()
        raw.edit().putString("profile", Base64.encodeToString(bytes, Base64.NO_WRAP)).commit()
        assertThrows(SecurityException::class.java) { store.getString("profile", null) }
    }
}
