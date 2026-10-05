package com.qeli;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Process;
import android.util.Log;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;

/** Standalone test APK process: use only platform Java classes, no target APK dependencies. */
public final class SystemNetworkProbeReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        final String tag = intent.getStringExtra("tag");
        if (!"Q29BASELINE".equals(tag) && !"Q29PROTECTED".equals(tag) && !"Q29BLOCKED".equals(tag) && !"Q29DEAD".equals(tag) && !"Q29RECOVERED".equals(tag) && !"Q29MANUAL".equals(tag)) return;
        final PendingResult pending = goAsync();
        Thread worker = new Thread(() -> {
            try (DatagramSocket socket = new DatagramSocket()) {
                socket.setSoTimeout(1500);
                socket.connect(InetAddress.getByName("198.19.0.1"), 26000);
                byte[] data = tag.getBytes(StandardCharsets.UTF_8);
                socket.send(new DatagramPacket(data, data.length));
                DatagramPacket reply = new DatagramPacket(new byte[256], 256);
                socket.receive(reply);
                Log.i("Q29Probe", "COMPLETE tag=" + tag + " uid=" + Process.myUid() + " source=" +
                    socket.getLocalAddress().getHostAddress() + " reply=" +
                    new String(reply.getData(), 0, reply.getLength(), StandardCharsets.UTF_8));
            } catch (Exception error) {
                Log.i("Q29Probe", "COMPLETE tag=" + tag + " uid=" + Process.myUid() + " error=" +
                    error.getClass().getSimpleName() + ":" + error.getMessage());
            } finally { pending.finish(); }
        }, "q29-independent-socket");
        worker.setDaemon(true);
        worker.start();
    }
}
