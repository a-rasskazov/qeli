import plistlib
import tempfile
import unittest
import zipfile
from pathlib import Path

import verify_ios_ipa


class IOSIPAVerifierTests(unittest.TestCase):
    def build_ipa(
        self,
        path: Path,
        *,
        keychain_group: str = "ABCDEFGHIJ.ru.qeli.app.shared",
        include_signatures: bool = True,
        tunnel_app_group: str = "group.ru.qeli.app",
    ) -> None:
        main_root = "Payload/Qeli.app/"
        tunnel_root = main_root + "PlugIns/QeliPacketTunnel.appex/"
        widget_root = main_root + "PlugIns/QeliWidgets.appex/"
        main = {
            "CFBundleIdentifier": "ru.qeli.app",
            "QeliPacketTunnelBundleIdentifier": "ru.qeli.app.PacketTunnel",
            "QeliAppGroup": "group.ru.qeli.app",
            "QeliKeychainAccessGroup": keychain_group,
        }
        tunnel = {
            "CFBundleIdentifier": "ru.qeli.app.PacketTunnel",
            "QeliAppGroup": tunnel_app_group,
            "QeliKeychainAccessGroup": keychain_group,
            "NSExtension": {
                "NSExtensionPointIdentifier": "com.apple.networkextension.packet-tunnel"
            },
        }
        widget = {
            "CFBundleIdentifier": "ru.qeli.app.Widgets",
            "QeliAppGroup": "group.ru.qeli.app",
            "NSExtension": {"NSExtensionPointIdentifier": "com.apple.widgetkit-extension"},
        }
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(main_root + "Info.plist", plistlib.dumps(main))
            archive.writestr(tunnel_root + "Info.plist", plistlib.dumps(tunnel))
            archive.writestr(widget_root + "Info.plist", plistlib.dumps(widget))
            for root in (main_root, tunnel_root, widget_root):
                archive.writestr(root + "binary", b"binary")
                if include_signatures:
                    archive.writestr(root + "embedded.mobileprovision", b"profile")
                    archive.writestr(root + "_CodeSignature/CodeResources", b"signature")

    def test_accepts_consistent_structural_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qeli.ipa"
            self.build_ipa(path)
            errors, facts = verify_ios_ipa.validate_archive(path)
            self.assertEqual(errors, [])
            self.assertEqual(facts["tunnel_id"], "ru.qeli.app.PacketTunnel")
            self.assertEqual(facts["app_group"], "group.ru.qeli.app")

    def test_rejects_unsigned_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qeli.ipa"
            self.build_ipa(path, include_signatures=False)
            errors, _ = verify_ios_ipa.validate_archive(path)
            self.assertEqual(sum("code signature is missing" in error for error in errors), 3)
            self.assertEqual(sum("embedded.mobileprovision is missing" in error for error in errors), 3)

    def test_rejects_keychain_group_without_team_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qeli.ipa"
            self.build_ipa(path, keychain_group="ru.qeli.app.shared")
            errors, _ = verify_ios_ipa.validate_archive(path)
            self.assertIn(
                "QeliKeychainAccessGroup lacks the ten-character Apple Team/AppIdentifier prefix",
                errors,
            )

    def test_rejects_component_group_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qeli.ipa"
            self.build_ipa(path, tunnel_app_group="group.wrong")
            errors, _ = verify_ios_ipa.validate_archive(path)
            self.assertIn("container and Packet Tunnel App Group values differ", errors)


if __name__ == "__main__":
    unittest.main()
