"""Offline release discovery and integrity tests (no GitHub requests)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from published_networks import (list_published_networks, download_published_network,
                                PublishedNetworkCancelled)


class ListingResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


class DownloadResponse:
    def __init__(self, chunks, url, status_code=200, headers=None):
        self.chunks, self.url = chunks, url
        self.status_code = status_code
        self.headers = headers or {}
    def __enter__(self):return self
    def __exit__(self, *args):return False
    def raise_for_status(self):pass
    def iter_content(self, chunk_size=1024*1024):yield from self.chunks


class FakeSession:
    def __init__(self, releases=None, chunks=None):
        self.releases = releases or []
        self.chunks = chunks or []
        self.requests = []
    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        if '/repos/' in url:
            return ListingResponse(self.releases)
        return DownloadResponse(self.chunks, url)


class PublishedNetworkTests(unittest.TestCase):
    def _asset(self, data, digest=None):
        return {'id': 123, 'name': 'association.sqlite3', 'size': len(data),
                'state': 'uploaded', 'digest': digest or 'sha256:' + hashlib.sha256(data).hexdigest(),
                'url':'https://github.com/jjy246/FLIN-Research-Desktop/releases/download/network-v1/association.sqlite3',
                'browser_download_url':
                'https://github.com/jjy246/FLIN-Research-Desktop/releases/download/network-v1/association.sqlite3'}

    def test_list_includes_approved_community_and_owner_releases(self):
        data=b'SQLite format 3\x00' + b'\x00'*128
        community=self._asset(data)
        release=[{'tag_name':'community-bob-v1','name':'Bob network','draft':False,
                  'published_at':'2026-10-16T02:00:00Z','assets':[community]},
                 {'tag_name':'network-v1','name':'Maintainer','draft':False,
                  'assets':[dict(community,id=124)]},
                 {'tag_name':'draft','draft':True,'assets':[community]},
                 {'tag_name':'unrelated','assets':[{'name':'source.zip','size':100,'id':99}]}]
        result=list_published_networks(FakeSession(releases=release))
        self.assertEqual(len(result),2)
        self.assertEqual({x['tag'] for x in result},{'network-v1','community-bob-v1'})

    def test_download_verifies_size_hash_and_header(self):
        data=b'SQLite format 3\x00'+ b'\x00'*1024
        asset=self._asset(data)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'received.sqlite3'
            info=download_published_network(asset,target,session=FakeSession(chunks=[data[:33],data[33:]]))
            self.assertEqual(target.read_bytes(),data)
            self.assertEqual(info['sha256'], hashlib.sha256(data).hexdigest())

    def test_invalid_digest_and_partial_download_are_removed(self):
        data=b'SQLite format 3\x00'+ b'\x00'*256
        asset=self._asset(data,digest='sha256:'+'0'*64)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'download.sqlite3'
            with self.assertRaisesRegex(ValueError,'SHA-256'):
                download_published_network(asset,target,session=FakeSession(chunks=[data]))
            self.assertFalse(target.exists())
            asset=self._asset(data)
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                download_published_network(asset,target,session=FakeSession(chunks=[data[:20]]))
            self.assertFalse(target.exists())

    def test_rejects_untrusted_redirect_before_fetching_it(self):
        data=b'SQLite format 3\x00' + b'\x00'*32
        asset=self._asset(data)
        class RedirectSession(FakeSession):
            def get(self, url, **kwargs):
                self.requests.append((url,kwargs))
                return DownloadResponse([],url,status_code=302,
                    headers={'Location':'https://127.0.0.1/private'})
        client=RedirectSession()
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'x.sqlite3'
            with self.assertRaisesRegex(ValueError,'trusted HTTPS hosts'):
                download_published_network(asset,target,session=client)
            self.assertEqual(len(client.requests),1)
            self.assertFalse(target.exists())

    def test_rejects_non_official_links(self):
        data=b'SQLite format 3\x00'+ b'\x00'*32
        asset=self._asset(data)
        asset['url']='https://example.net/file.sqlite3'
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                download_published_network(asset,Path(td)/'x.sqlite3',session=FakeSession(chunks=[data]))


if __name__=='__main__':unittest.main()
