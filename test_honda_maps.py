import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import honda_maps as h

class Response(io.BytesIO):
    def __init__(self, data, status=200, headers=None):
        super().__init__(data); self.status=status; self.headers=headers or {}

class ClientTests(unittest.TestCase):
    def item(self, data=b'abcdef'):
        return {'name':'NavDB.TEST/test.nds','url':'https://example.invalid/file','size':len(data),'md5':hashlib.md5(data).hexdigest()}
    def test_vin_requires_consent(self):
        with patch.object(h,'build_opener') as network:
            with self.assertRaises(h.DownloadError):h.link_from_vin('A'*17)
            network.assert_not_called()
    def test_invalid_vin_rejected_before_network(self):
        with patch.object(h,'build_opener') as network:
            with self.assertRaises(h.DownloadError):h.link_from_vin('invalid',True)
            network.assert_not_called()
    def test_range_resume(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.nds';p.with_name('file.nds.honda-part').write_bytes(b'abc')
            with patch.object(h,'request',return_value=Response(b'def',206,{'Content-Range':'bytes 3-5/6'})) as request:
                h.transfer(self.item(),p)
                self.assertEqual(request.call_args.args[1],3)
                self.assertEqual(p.read_bytes(),b'abcdef')
    def test_server_ignores_range(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.nds';p.with_name('file.nds.honda-part').write_bytes(b'abc')
            with patch.object(h,'request',return_value=Response(b'abcdef')):
                h.transfer(self.item(),p)
                self.assertEqual(p.read_bytes(),b'abcdef')
    def test_wrong_range_does_not_commit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.nds';p.with_name('file.nds.honda-part').write_bytes(b'abc')
            with patch.object(h,'time'),patch.object(h,'request',side_effect=lambda *a:Response(b'def',206,{'Content-Range':'bytes 0-2/6'})):
                with self.assertRaises(h.DownloadError):h.transfer(self.item(),p)
            self.assertFalse(p.exists())
    def test_hash_error_does_not_commit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.nds'
            with patch.object(h,'time'),patch.object(h,'request',side_effect=lambda *a:Response(b'badbad')):
                with self.assertRaises(h.DownloadError):h.transfer(self.item(),p)
            self.assertFalse(p.exists())
    def test_existing_wrong_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.nds';p.write_bytes(b'old')
            with self.assertRaises(h.DownloadError):h.transfer(self.item(),p)
            self.assertEqual(p.read_bytes(),b'old')
    def test_existing_valid_file_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.nds';p.write_bytes(b'abcdef')
            with patch.object(h,'request') as r:
                h.transfer(self.item(),p);r.assert_not_called()
    def test_symbolic_target_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'NavDB.TEST').symlink_to('/tmp')
            with self.assertRaises(h.DownloadError):h.target_path(root,'NavDB.TEST/a')
    def catalog(self,name='NavDB.TEST/test.nds'):
        i=self.item()
        return {'parameters':{'program':'bonneville','market':'EU'},'distribution':{'1':{'links':[
            {'rel':'nds.drm','href':'https://example.invalid/license','otherAttributes':{'local-id':'PACKAGE.SLIST'}},
            {'rel':'nds.file','href':i['url'],'length':i['size'],'hash':'md5:'+i['md5'],'otherAttributes':{'local-id':name}}]}}}
    def test_traversal_rejected(self):
        for name in ['../escape','/abs','a/../escape','a\\escape','a//b','a/./b']:
            with self.subTest(name=name),self.assertRaises(h.DownloadError):h.plan(self.catalog(name))
    def test_license_last(self):
        _,items=h.plan(self.catalog());self.assertEqual(items[-1]['name'],'PACKAGE.SLIST')
    def test_unsupported_relation_rejected(self):
        c=self.catalog();c['distribution']['1']['links'][1]['rel']='applicationConfiguration'
        with self.assertRaises(h.DownloadError):h.plan(c)
    def test_fat_duplicate_rejected(self):
        c=self.catalog();links=c['distribution']['1']['links'];links.append(dict(links[1],otherAttributes={'local-id':'navdb.test/TEST.NDS'}))
        with self.assertRaises(h.DownloadError):h.plan(c)
    def test_license_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'PACKAGE.SLIST';i={'name':p.name,'url':'https://example.invalid/license','size':None,'md5':None}
            with patch.object(h,'request',return_value=Response(b'LICENSE\0\xff')):h.transfer(i,p)
            self.assertEqual(p.read_bytes(),b'LICENSE\0\xff')

if __name__=='__main__':unittest.main()
