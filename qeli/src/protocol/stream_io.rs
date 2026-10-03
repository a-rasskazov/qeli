use tokio::io::{AsyncWrite, AsyncWriteExt};

/// Finish one protocol write before waiting for a peer response or recording delivery.
/// Buffered wire adapters may accept plaintext before their socket is writable.
/// Keep this boundary identical in daemon and native-core session/data pumps.
pub(crate) trait WriteAllFlush: AsyncWrite + Unpin {
    async fn write_all_flush(&mut self, bytes: &[u8]) -> std::io::Result<()> {
        self.write_all(bytes).await?;
        self.flush().await
    }
}
impl<W: AsyncWrite + Unpin + ?Sized> WriteAllFlush for W {}
