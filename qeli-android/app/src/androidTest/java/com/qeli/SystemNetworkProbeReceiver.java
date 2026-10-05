package com.qeli;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Process;
import android.util.Log;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;

/** Standalone test APK process: platform Java only, ordinary UID traffic without bind/protect. */
public final class SystemNetworkProbeReceiver extends BroadcastReceiver {
    private static String sha(byte[] data) throws Exception {
        StringBuilder hex = new StringBuilder();
        for (byte value : MessageDigest.getInstance("SHA-256").digest(data)) hex.append(String.format("%02x", value & 255));
        return hex.toString();
    }
    @Override public void onReceive(Context context, Intent intent) {
        final String tag = intent.getStringExtra("tag");
        if (!"Q29BASELINE".equals(tag) && !"Q29PROTECTED".equals(tag) && !"Q29BLOCKED".equals(tag) && !"Q29DEAD".equals(tag) && !"Q29RECOVERED".equals(tag) && !"Q29MANUAL".equals(tag)) return;
        final String family = intent.hasExtra("family") ? intent.getStringExtra("family") : "ipv4";
        final String protocol = intent.hasExtra("protocol") ? intent.getStringExtra("protocol") : "udp";
        final int size = intent.getIntExtra("payload_bytes", tag.length());
        if ((!"ipv4".equals(family) && !"ipv6".equals(family)) || (!"tcp".equals(protocol) && !"udp".equals(protocol)) || (size != tag.length() && size != 257 && size != 16384)) return;
        final int run = intent.getIntExtra("burst_run", 0);
        final int count = intent.getIntExtra("burst_count", 0);
        if (run < 0 || (run != 0 && (count < 1 || count > 12)) || (run == 0 && count != 0)) return;
        final PendingResult pending = goAsync();
        Thread worker = new Thread(() -> {
            try {
                if (run == 0) {
                    probe(tag, family, protocol, size, 0, 0, "COMPLETE tag=" + tag + " uid=" + Process.myUid() + " family=" + family + " protocol=" + protocol + " bytes=" + size);
                } else {
                    Thread[] children = new Thread[4];
                    int at = 0;
                    for (String f : new String[]{"ipv4", "ipv6"}) {
                        for (String proto : new String[]{"tcp", "udp"}) {
                            final String selectedFamily = f, selectedProtocol = proto;
                            children[at] = new Thread(() -> {
                                Log.i("Q29Probe", "BURST_BEGIN run=" + run + " uid=" + Process.myUid() + " family=" + selectedFamily + " protocol=" + selectedProtocol + " count=" + count);
                                for (int sample = 0; sample < count; sample++) {
                                    String prefix = "BURST run=" + run + " sample=" + sample + " tag=" + tag + " uid=" + Process.myUid() + " family=" + selectedFamily + " protocol=" + selectedProtocol + " bytes=257 started_ms=" + System.currentTimeMillis();
                                    probe(tag, selectedFamily, selectedProtocol, 257, run, sample, prefix);
                                    try { Thread.sleep(150); }
                                    catch (InterruptedException error) { Thread.currentThread().interrupt(); return; }
                                }
                            }, "q29-burst-" + selectedFamily + "-" + selectedProtocol);
                            children[at].setDaemon(true);children[at++].start();
                        }
                    }
                    boolean interrupted = false;
                    for (Thread child : children) {
                        while (child.isAlive()) {
                            try { child.join(); }
                            catch (InterruptedException error) { interrupted = true; }
                        }
                    }
                    if (interrupted) Thread.currentThread().interrupt();
                    Log.i("Q29Probe", "BURST_FINISHED run=" + run + " uid=" + Process.myUid());
                }
            } finally { pending.finish(); }
        }, "q29-independent-socket");
        worker.setDaemon(true); worker.start();
    }

    private static void probe(String tag, String family, String protocol, int size, int run, int sample, String prefix) {
            try {
                InetAddress host = InetAddress.getByName("ipv6".equals(family) ? "2001:db8:29::1" : "198.19.0.1");
                byte[] data = new byte[size];
                for (int i = 0; i < data.length; i++) data[i] = (byte) ((i * 31 + 17) % 251);
                byte[] marker = tag.getBytes(StandardCharsets.UTF_8);
                System.arraycopy(marker, 0, data, 0, marker.length);
                if (run != 0) {
                    for (int shift = 0; shift < 4; shift++) {
                        data[marker.length + shift] = (byte) (run >>> (24 - 8 * shift));
                        data[marker.length + 4 + shift] = (byte) (sample >>> (24 - 8 * shift));
                    }
                }
                byte[] expected, received;
                String source;
                if ("tcp".equals(protocol)) {
                    expected = data.clone();
                    for (int i = 0; i < data.length; i++) expected[i] = data[data.length - 1 - i];
                    try (Socket socket = new Socket()) {
                        socket.setSoTimeout(run == 0 ? 3000 : 250);
                        socket.connect(new InetSocketAddress(host, 26000), run == 0 ? 2000 : 250);
                        source = socket.getLocalAddress().getHostAddress();
                        DataOutputStream output = new DataOutputStream(socket.getOutputStream());
                        output.writeInt(data.length); output.write(data); output.flush();
                        DataInputStream input = new DataInputStream(socket.getInputStream());
                        if (input.readInt() != data.length) throw new IllegalStateException("TCP reply length differs");
                        received = new byte[data.length]; input.readFully(received);
                    }
                } else {
                    expected = new byte[data.length + 4];
                    System.arraycopy("Q29:".getBytes(StandardCharsets.UTF_8), 0, expected, 0, 4);
                    System.arraycopy(data, 0, expected, 4, data.length);
                    try (DatagramSocket socket = new DatagramSocket()) {
                        socket.setSoTimeout(run == 0 ? 1500 : 250); socket.connect(host, 26000);
                        source = socket.getLocalAddress().getHostAddress();
                        socket.send(new DatagramPacket(data, data.length));
                        DatagramPacket reply = new DatagramPacket(new byte[expected.length + 1], expected.length + 1);
                        socket.receive(reply);
                        received = Arrays.copyOfRange(reply.getData(), reply.getOffset(), reply.getOffset() + reply.getLength());
                    }
                }
                if (!Arrays.equals(expected, received)) throw new IllegalStateException("Payload bytes differ");
                Log.i("Q29Probe", prefix + (run == 0 ? "" : " done_ms=" + System.currentTimeMillis()) + " source=" + source + " reply=Q29:" + tag + " sha256=" + sha(data) + " reply_sha256=" + sha(received));
            } catch (Exception error) {
                Log.i("Q29Probe", prefix + (run == 0 ? "" : " done_ms=" + System.currentTimeMillis()) + " error=" + error.getClass().getSimpleName() + ":" + error.getMessage());

            }
    }
}
