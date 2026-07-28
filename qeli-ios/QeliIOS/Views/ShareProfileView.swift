import SwiftUI

struct ShareProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var copied = false
    let profile: Profile

    private var link: String {
        (try? VPNConfig(parsing: profile.configText).toQeliURI(label: profile.name)) ?? ""
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                if let image = QRCodeGenerator.image(for: link) {
                    Image(uiImage: image)
                        .interpolation(.none)
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: 270)
                        .padding(14)
                        .background(.white, in: RoundedRectangle(cornerRadius: 18))
                }
                Text(link)
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
                    .lineLimit(7)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .qeliCard()
                HStack(spacing: 12) {
                    // Explicit Copy, matching the Android share dialog: selecting the
                    // monospaced link by hand is fiddly, and the share sheet is a detour
                    // when the user just wants it on the clipboard.
                    Button {
                        UIPasteboard.general.string = link
                        copied = true
                    } label: {
                        Label(copied ? "Link copied" : "Copy", systemImage: copied ? "checkmark" : "doc.on.doc")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    ShareLink(item: link) {
                        Label("Share profile", systemImage: "square.and.arrow.up")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(QeliTheme.primary)
                }
                Text("The share link contains the profile credentials.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .padding()
            .navigationTitle("Share “\(profile.name)”")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
}

