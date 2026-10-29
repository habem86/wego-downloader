import hashlib
import io
import json
import contextlib
import sys
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
        _,items=h.plan(self.catalog());self.assertEqual(items[-1]['name'],'HereMapsV1/PACKAGE.SLIST')
    def test_unsupported_relation_rejected(self):
        c=self.catalog();c['distribution']['1']['links'][1]['rel']='applicationConfiguration'
        with self.assertRaises(h.DownloadError):h.plan(c)
    def test_fat_duplicate_rejected(self):
        c=self.catalog();links=c['distribution']['1']['links'];links.append(dict(links[1],otherAttributes={'local-id':'navdb.test/TEST.NDS'}))
        with self.assertRaises(h.DownloadError):h.plan(c)
    def test_catalog_paths_match_observed_usb_layout(self):
        _,items=h.plan(self.catalog('NavDB.CZE_1109/3DO.NDS'))
        self.assertEqual({x['name'] for x in items},{'HereMapsV1/NavDB.CZE_1109/3DO.NDS','HereMapsV1/PACKAGE.SLIST'})
    def test_catalog_prefix_and_release_are_combined(self):
        c=self.catalog();c['parameters']['path']='MapsV';c['distribution']['2']=c['distribution'].pop('1')
        _,items=h.plan(c)
        self.assertTrue(all(x['name'].startswith('MapsV2/') for x in items))
    def test_multiple_releases_have_separate_paths(self):
        c=self.catalog();c['distribution']['2']=c['distribution']['1']
        _,items=h.plan(c)
        self.assertEqual(len(items),4)
        self.assertEqual({x['name'].split('/')[0] for x in items},{'HereMapsV1','HereMapsV2'})
    def test_unsafe_prefix_or_release_is_rejected(self):
        for value in ['../escape','/absolute','Maps/','.', '..', 'bad.']:
            with self.subTest(value=value):
                c=self.catalog();c['parameters']['path']=value
                with self.assertRaises(h.DownloadError):h.plan(c)
                c=self.catalog();c['distribution'][value]=c['distribution'].pop('1')
                with self.assertRaises(h.DownloadError):h.plan(c)
    def test_download_writes_map_tree_and_license_inside_release_folder(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);usb=base/'USB';usb.mkdir();catalog=base/'catalog.json'
            c=self.catalog('NavDB.CZE_1109/U1109/test.nds');catalog.write_text(json.dumps(c))
            def response(url,offset=0):
                return Response(b'abcdef' if url.endswith('/file') else b'LICENSE')
            with patch.object(sys,'argv',['honda_maps.py','--catalog',str(catalog),'--dest',str(usb),'--download']),patch.object(h,'request',side_effect=response),patch.object(h.os,'sync'),contextlib.redirect_stdout(io.StringIO()):
                h.main()
            self.assertEqual((usb/'HereMapsV1/NavDB.CZE_1109/U1109/test.nds').read_bytes(),b'abcdef')
            self.assertEqual((usb/'HereMapsV1/PACKAGE.SLIST').read_bytes(),b'LICENSE')
            self.assertFalse((usb/'NavDB.CZE_1109').exists())
            self.assertFalse((usb/'PACKAGE.SLIST').exists())
    def test_release_folder_cannot_be_selected_as_usb_root(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);usb=base/'HereMapsV1';usb.mkdir();catalog=base/'catalog.json';catalog.write_text(json.dumps(self.catalog()))
            with patch.object(sys,'argv',['honda_maps.py','--catalog',str(catalog),'--dest',str(usb),'--download']),patch.object(h,'request') as request,contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(h.DownloadError):h.main()
                request.assert_not_called()
            self.assertEqual(list(usb.iterdir()),[])
    def test_legacy_root_layout_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);usb=base/'USB';usb.mkdir();(usb/'NavDB.CZE_1109').mkdir();catalog=base/'catalog.json';catalog.write_text(json.dumps(self.catalog()))
            with patch.object(sys,'argv',['honda_maps.py','--catalog',str(catalog),'--dest',str(usb),'--download']),patch.object(h,'request') as request,contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(h.DownloadError):h.main()
                request.assert_not_called()
            self.assertFalse((usb/'HereMapsV1').exists())
    def test_license_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'PACKAGE.SLIST';i={'name':p.name,'url':'https://example.invalid/license','size':None,'md5':None}
            with patch.object(h,'request',return_value=Response(b'LICENSE\0\xff')):h.transfer(i,p)
            self.assertEqual(p.read_bytes(),b'LICENSE\0\xff')

if __name__=='__main__':unittest.main()
