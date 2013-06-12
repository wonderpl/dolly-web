import hmac
import hashlib
import uuid
from mock import patch
from rockpack.mainsite.services.video.models import Channel, Video
from rockpack.mainsite.services.pubsubhubbub.api import subscribe
from rockpack.mainsite.services.pubsubhubbub.models import Subscription
from ..base import RockPackTestCase
from ..fixtures import UserData


PUSH_ATOM_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xmlns:openSearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:gd="http://schemas.google.com/g/2005" xmlns:yt="http://gdata.youtube.com/schemas/2007" gd:etag="W/&quot;A0ADSX05fSp7I2A9WhBUGUs.&quot;">
  <id>tag:youtube.com,2008:user:JLovesMac1:uploads</id>
  <updated>2013-05-07T23:36:18.325Z</updated>
  <category scheme="http://schemas.google.com/g/2005#kind" term="http://gdata.youtube.com/schemas/2007#video"/>
  <title>Uploads by JLovesMac1</title>
  <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
  <link rel="related" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/jlovesmac1?v=2"/>
  <link rel="alternate" type="text/html" href="http://www.youtube.com/channel/UCeiunpfG3pQlnla6rvEicDQ/videos"/>
  <link rel="hub" href="http://pubsubhubbub.appspot.com"/>
  <link rel="http://schemas.google.com/g/2005#feed" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/JLovesMac1/uploads?v=2"/>
  <link rel="http://schemas.google.com/g/2005#batch" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/JLovesMac1/uploads/batch?v=2"/>
  <link rel="self" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/JLovesMac1/uploads?start-index=1&amp;max-results=25&amp;v=2"/>
  <link rel="service" type="application/atomsvc+xml" href="http://gdata.youtube.com/feeds/api/users/JLovesMac1/uploads?alt=atom-service&amp;v=2"/>
  <link rel="next" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/JLovesMac1/uploads?start-index=26&amp;max-results=25&amp;v=2"/>
  <author>
    <name>JLovesMac1</name>
    <uri>http://gdata.youtube.com/feeds/api/users/JLovesMac1</uri>
    <yt:userId>eiunpfG3pQlnla6rvEicDQ</yt:userId>
  </author>
  <generator version="2.1" uri="http://gdata.youtube.com">YouTube data API</generator>
  <openSearch:totalResults>286</openSearch:totalResults>
  <openSearch:startIndex>1</openSearch:startIndex>
  <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
  %s
</feed>
'''
PUSH_ENTRY_XML = '''
  <entry gd:etag="W/&quot;A0ADQX47eCp7I2A9WhBUGUs.&quot;">
    <id>tag:youtube.com,2008:video:%(videoid)s</id>
    <published>2013-05-07T23:35:46.000Z</published>
    <updated>2013-05-07T23:36:10.000Z</updated>
    <category scheme="http://schemas.google.com/g/2005#kind" term="http://gdata.youtube.com/schemas/2007#video"/>
    <category scheme="http://gdata.youtube.com/schemas/2007/categories.cat" term="Howto" label="Howto &amp; Style"/>
    <title>Beauty Pet Peeve?</title>
    <content type="application/x-shockwave-flash" src="http://www.youtube.com/v/Z3f4kQLtfEQ?version=3&amp;f=user_uploads&amp;d=AdQyB2zoOhT3oQL1BqTK5sIO88HsQjpE1a8d1GxQnGDm&amp;app=youtube_gdata"/>
    <link rel="alternate" type="text/html" href="http://www.youtube.com/watch?v=Z3f4kQLtfEQ&amp;feature=youtube_gdata"/>
    <link rel="http://gdata.youtube.com/schemas/2007#video.responses" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/videos/Z3f4kQLtfEQ/responses?v=2"/>
    <link rel="http://gdata.youtube.com/schemas/2007#video.ratings" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/videos/Z3f4kQLtfEQ/ratings?v=2"/>
    <link rel="http://gdata.youtube.com/schemas/2007#video.complaints" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/videos/Z3f4kQLtfEQ/complaints?v=2"/>
    <link rel="http://gdata.youtube.com/schemas/2007#video.related" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/videos/Z3f4kQLtfEQ/related?v=2"/>
    <link rel="http://gdata.youtube.com/schemas/2007#uploader" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/eiunpfG3pQlnla6rvEicDQ?v=2"/>
    <link rel="self" type="application/atom+xml" href="http://gdata.youtube.com/feeds/api/users/JLovesMac1/uploads/Z3f4kQLtfEQ?v=2"/>
    <author>
      <name>JLovesMac1</name>
      <uri>http://gdata.youtube.com/feeds/api/users/JLovesMac1</uri>
      <yt:userId>eiunpfG3pQlnla6rvEicDQ</yt:userId>
    </author>
    <yt:accessControl action="comment" permission="allowed"/>
    <yt:accessControl action="commentVote" permission="allowed"/>
    <yt:accessControl action="videoRespond" permission="moderated"/>
    <yt:accessControl action="rate" permission="allowed"/>
    <yt:accessControl action="embed" permission="allowed"/>
    <yt:accessControl action="list" permission="allowed"/>
    <yt:accessControl action="autoPlay" permission="allowed"/>
    <yt:accessControl action="syndicate" permission="allowed"/>
    <gd:comments>
      <gd:feedLink rel="http://gdata.youtube.com/schemas/2007#comments" href="http://gdata.youtube.com/feeds/api/videos/Z3f4kQLtfEQ/comments?v=2" countHint="1"/>
    </gd:comments>
    <media:group>
      <media:category label="Howto &amp; Style" scheme="http://gdata.youtube.com/schemas/2007/categories.cat">Howto</media:category>
      <media:content url="http://www.youtube.com/v/Z3f4kQLtfEQ?version=3&amp;f=user_uploads&amp;d=AdQyB2zoOhT3oQL1BqTK5sIO88HsQjpE1a8d1GxQnGDm&amp;app=youtube_gdata" type="application/x-shockwave-flash" medium="video" isDefault="true" expression="full" duration="248" yt:format="5"/>
      <media:credit role="uploader" scheme="urn:youtube" yt:display="JLovesMac1" yt:type="partner">jlovesmac1</media:credit>
      <media:description type="plain">I GOT MINE HERE!</media:description>
      <media:keywords/>
      <media:license type="text/html" href="http://www.youtube.com/t/terms">youtube</media:license>
      <media:player url="http://www.youtube.com/watch?v=Z3f4kQLtfEQ&amp;feature=youtube_gdata_player"/>
      <media:restriction type="country" relationship="deny">BQ CW DE SS SX</media:restriction>
      <media:thumbnail url="http://i.ytimg.com/vi/Z3f4kQLtfEQ/default.jpg" height="90" width="120" time="00:02:04" yt:name="default"/>
      <media:thumbnail url="http://i.ytimg.com/vi/Z3f4kQLtfEQ/mqdefault.jpg" height="180" width="320" yt:name="mqdefault"/>
      <media:thumbnail url="http://i.ytimg.com/vi/Z3f4kQLtfEQ/hqdefault.jpg" height="360" width="480" yt:name="hqdefault"/>
      <media:thumbnail url="http://i.ytimg.com/vi/Z3f4kQLtfEQ/1.jpg" height="90" width="120" time="00:01:02" yt:name="start"/>
      <media:thumbnail url="http://i.ytimg.com/vi/Z3f4kQLtfEQ/2.jpg" height="90" width="120" time="00:02:04" yt:name="middle"/>
      <media:thumbnail url="http://i.ytimg.com/vi/Z3f4kQLtfEQ/3.jpg" height="90" width="120" time="00:03:06" yt:name="end"/>
      <media:title type="plain">Beauty Pet Peeve?</media:title>
      <yt:aspectRatio>widescreen</yt:aspectRatio>
      <yt:duration seconds="248"/>
      <yt:uploaded>2013-05-07T23:35:46.000Z</yt:uploaded>
      <yt:uploaderId>UCeiunpfG3pQlnla6rvEicDQ</yt:uploaderId>
      <yt:videoid>%(videoid)s</yt:videoid>
    </media:group>
    <yt:statistics favoriteCount="0" viewCount="2"/>
  </entry>
'''


class PubSubHubbubTestCase(RockPackTestCase):

    @patch('rockpack.mainsite.requests.post')
    def setUp(self, requests_post):
        super(PubSubHubbubTestCase, self).setUp()
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        self.channel = Channel(title='', description='', cover='', owner=UserData.test_user_a.id).save()
        assert Channel.query.get(self.channel.id), channel.id
        self.channel.add_meta('en-us')
        self.subid = subscribe('test', uuid.uuid4().hex, self.channel.id).id

    def tearDown(self):
        self.ctx.pop()
        super(PubSubHubbubTestCase, self).tearDown()

    def test_verify(self):
        subs = Subscription.query.get(self.subid)
        self.assertFalse(bool(subs.verified))
        with self.app.test_client() as client:
            r = client.get(
                '/ws/pubsubhubbub/callback',
                query_string={
                    'id': subs.id,
                    'hub.topic': subs.topic,
                    'hub.challenge': 123,
                    'hub.verify_token': subs.verify_token,
                    'hub.mode': 'subscribe',
                    'hub.lease_seconds': 60,
                })
            self.assertEquals(r.status_code, 200)
        self.assertTrue(subs.verified)

    def _post_entries(self, subs, data):
        sig = hmac.new(subs.secret, data, hashlib.sha1)
        with self.app.test_client() as client:
            r = client.post(
                '/ws/pubsubhubbub/callback',
                query_string={'id': subs.id},
                content_type='application/atom+xml',
                data=data,
                headers={'X-Hub-Signature': 'sha1=' + sig.hexdigest()})
            self.assertEquals(r.status_code, 204)

    def test_post(self):
        entry = PUSH_ENTRY_XML % dict(videoid='xyzzy')
        data = PUSH_ATOM_XML % dict(entry=entry)
        subs = Subscription.query.get(self.subid)
        self._post_entries(subs, data)
        video = subs.channel.video_instances[0].video_rel
        self.assertEquals(video.source_videoid, 'xyzzy')
        self.assertEquals(video.duration, 248)
        self.assertIn('BQ', [rst.country for rst in video.restrictions])

    def test_post_update(self):
        # Double-check that subsequent updates and repeated videos
        # are handled correctly.
        ids = map(str, range(3))
        entry = PUSH_ENTRY_XML % dict(videoid=ids[0])
        for id in ids:
            entry += PUSH_ENTRY_XML % dict(videoid=id)
            data = PUSH_ATOM_XML % dict(entry=entry)
            subs = Subscription.query.get(self.subid)
            self._post_entries(subs, data)
        channel_videos = [
            v.video_rel.source_videoid for v in subs.channel.video_instances]
        self.assertEquals(sorted(channel_videos), ids)
