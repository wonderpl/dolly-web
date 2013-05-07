import hmac
import hashlib
import uuid
from mock import patch
from rockpack.mainsite.services.pubsubhubbub.api import subscribe
from rockpack.mainsite.services.pubsubhubbub.models import Subscription
from ..base import RockPackTestCase
from ..fixtures import ChannelData


# From http://gdata.youtube.com/feeds/api/videos?max-results=1
PUSH_ATOM_XML = '''<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'
      xmlns:openSearch='http://a9.com/-/spec/opensearch/1.1/'
      xmlns:media='http://search.yahoo.com/mrss/'
      xmlns:batch='http://schemas.google.com/gdata/batch'
      xmlns:yt='http://gdata.youtube.com/schemas/2007'
      xmlns:gd='http://schemas.google.com/g/2005'
      gd:etag='W/&quot;DU4DRX47eCp7ImA9WB9RFEU.&quot;'>
  <id>tag:youtube.com,2008:user:_x5XG1OV2P6uZZ5FSM9Ttw:subscriptions</id>
  <updated>2008-07-21T17:10:32.855Z</updated>
  <category scheme='http://schemas.google.com/g/2005#kind'
    term='http://gdata.youtube.com/schemas/2007#subscription'/>
  <title>Subscriptions of GoogleDevelopers</title>
  <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
  <link rel='related' type='application/atom+xml'
    href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw?v=2'/>
  <link rel='alternate' type='text/html'
    href='https://www.youtube.com'/>
  <link rel='hub' href='http://pubsubhubbub.appspot.com'/>
  <link rel='http://schemas.google.com/g/2005#feed'
    type='application/atom+xml'
    href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw/subscriptions?v=2'/>
  <link rel='http://schemas.google.com/g/2005#post'
    type='application/atom+xml'
    href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw/subscriptions?v=2'/>
  <link rel='http://schemas.google.com/g/2005#batch'
    type='application/atom+xml'
    href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw/subscriptions/batch?v=2'/>
  <link rel='self' type='application/atom+xml'
    href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw/subscriptions?...'/>
  <link rel='service' type='application/atomsvc+xml'
    href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw/subscriptions?alt=...'/>
  <author>
    <name>_x5XG1OV2P6uZZ5FSM9Ttw</name>
    <uri>https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw</uri>
    <yt:userId>_x5XG1OV2P6uZZ5FSM9Ttw</yt:userId>
  </author>
  <generator version='2.1'
    uri='http://gdata.youtube.com/'>YouTube data API</generator>
  <openSearch:totalResults>3</openSearch:totalResults>
  <openSearch:startIndex>1</openSearch:startIndex>
  <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
  <entry gd:etag='W/"CEAHQX47eCp7ImA9WxBSEUQ."'>
    <id>tag:youtube.com,2008:user:_x5XG1OV2P6uZZ5FSM9Ttw:subscription:ps2fD3tG7-s</id>
    <published>2009-12-18T19:18:50.000-08:00</published>
    <updated>2009-12-18T19:18:50.000-08:00</updated>
    <category scheme='http://schemas.google.com/g/2005#kind'
      term='http://gdata.youtube.com/schemas/2007#subscription'/>
    <category scheme='http://gdata.youtube.com/schemas/2007/subscriptiontypes.cat'
      term='user'/>
    <title>Activity of : GoogleTechTalks</title>
    <content type='application/atom+xml;type=feed'
      src='https://gdata.youtube.com/feeds/api/users/googletechtalks/events?v=2'/>
    <link rel='related' type='application/atom+xml'
      href='https://gdata.youtube.com/feeds/api/users/googletechtalks/events?v=2'/>
    <link rel='alternate' type='text/html'
      href='https://www.youtube.com/channel/UCtXKDgv1AVoG88PLl8nGXmw'/>
    <link rel='self' type='application/atom+xml'
      href='https://gdata.youtube.com/feeds/api/users/default/subscriptions/ps2fD3tG8-s?v=2'/>
    <link rel='edit' type='application/atom+xml'
      href='https://gdata.youtube.com/feeds/api/users/_x5XG1OV2P6uZZ5FSM9Ttw/subscriptions/MpajmvGNexIkHC?v=2'/>
    <author>
      <name>GoogleDevelopers</name>
      <uri>https://gdata.youtube.com/feeds/api/users/GoogleDevelopers</uri>
      <yt:userId>_x5XG1OV2P6uZZ5FSM9Ttw</yt:userId>
    </author>
    <yt:channelId>UCtXKDgv1AVoG88PLl8nGXmw</yt:channelId>
    <yt:countHint>1688</yt:countHint>
    <media:group>
      <media:category label='Music' scheme='http://gdata.youtube.com/schemas/2007/categories.cat'>Music</media:category>
      <media:content url='http://www.youtube.com/v/OpQFFLBMEPI?version=3&amp;f=videos&amp;app=youtube_gdata' type='application/x-shockwave-flash' medium='video' isDefault='true' expression='full' duration='243' yt:format='5'/>
      <media:credit role='uploader' scheme='urn:youtube' yt:display='PinkVEVO' yt:type='partner'>pinkvevo</media:credit>
      <media:description type='plain'/>
      <media:keywords/>
      <media:license type='text/html' href='http://www.youtube.com/t/terms'>youtube</media:license>
      <media:player url='http://www.youtube.com/watch?v=OpQFFLBMEPI&amp;feature=youtube_gdata_player'/>
      <media:restriction type='country' relationship='deny'>BQ CW DE SS SX</media:restriction>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/default.jpg' height='90' width='120' time='00:02:01.500' yt:name='default'/>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/sddefault.jpg' height='480' width='640' yt:name='sddefault'/>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/1.jpg' height='90' width='120' time='00:01:00.750' yt:name='start'/>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/2.jpg' height='90' width='120' time='00:02:01.500' yt:name='middle'/>
      <media:thumbnail url='http://i.ytimg.com/vi/OpQFFLBMEPI/3.jpg' height='90' width='120' time='00:03:02.250' yt:name='end'/>
      <media:title type='plain'>P!nk - Just Give Me A Reason ft. Nate Ruess</media:title>
      <yt:aspectRatio>widescreen</yt:aspectRatio>
      <yt:duration seconds='243'/>
      <yt:uploaded>2013-02-05T22:00:58.000Z</yt:uploaded>
      <yt:uploaderId>UCXJDX1KK6t121Z9FLhu5o2A</yt:uploaderId>
      <yt:videoid>OpQFFLBMEPI</yt:videoid>
    </media:group>
    <yt:unreadCount>5</yt:unreadCount>
    <yt:username display='GoogleTechTalks'>googletechtalks</yt:username>
  </entry>
</feed>
'''


class PubSubHubbubTestCase(RockPackTestCase):

    @patch('requests.post')
    def setUp(self, requests_post):
        super(PubSubHubbubTestCase, self).setUp()
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        self.subid = subscribe('test', uuid.uuid4().hex, ChannelData.channel1.id).id

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

    def test_post(self):
        subs = Subscription.query.get(self.subid)
        sig = hmac.new(subs.secret, PUSH_ATOM_XML, hashlib.sha1)
        with self.app.test_client() as client:
            r = client.post(
                '/ws/pubsubhubbub/callback',
                query_string={'id': subs.id},
                content_type='application/atom+xml',
                data=PUSH_ATOM_XML,
                headers={'X-Hub-Signature': 'sha1=' + sig.hexdigest()})
            self.assertEquals(r.status_code, 204)

        video = subs.channel.video_instances[0].video_rel
        self.assertEquals(video.source_videoid, 'OpQFFLBMEPI')
        self.assertEquals(video.duration, 243)
        self.assertIn('BQ', [r.country for r in video.restrictions])
        Subscription.query.session.delete(video)
