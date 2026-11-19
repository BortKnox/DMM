# DMM / PLAYBACK FIELD NOTES

[Back to the workbench](../README.md) · [Run locally](../README.md#run-it) · [Personal remote access](REMOTE-ACCESS.md)

These notes describe `feature/discovery-desk`. The playback observations below come from the earlier user and local checks recorded in the README; they are not new verification of every release or device.

## SAVING AND TORBOX

**Save to DMM** keeps a selected release, title and optional episode in the instance MongoDB database. It does not submit the release to TorBox. Saving the same release and episode twice updates one record. **Unsave** removes only the DMM record. You can also save a title before choosing a release.

The Library separates **Saved in DMM** from **TorBox downloads**. The TorBox tab reads the connected account; its delete action affects that account. It currently offers Play and Delete rather than a separate download button.

An uncached **Cache & Play** action submits the torrent. It does not wait for caching to finish and then start playback. Return to the release once it is available. The season cache action chooses a top result per episode, processes at most 30 episodes and can skip missing or failed results.

The TorBox resolver registers a torrent on the account to obtain torrent and file IDs, then requests a temporary download link. Playing a source or resolving a native-player URL can therefore add a TorBox dashboard entry. DMM does not automatically delete that entry. Playing an existing TorBox download requests its file link directly.

## DIRECT PLAYBACK

The browser tries the direct file URL first. Earlier checks confirmed playback and seeking on one 720p release. A separate H.264 release labelled DDP 5.1 produced a picture with silent audio. Browser, device and audio-track support vary; those checks do not establish support for arbitrary releases.

Use the chain-link control beside **Copy magnet** to resolve a temporary TorBox file URL. Paste it into VLC's **Open Network Stream** or MPC-HC's **Open File**. Generate a fresh link when it expires. Keep links private: anyone who has a valid file URL may be able to use it.

## SERVER CONVERSION

Select conversion in the player when direct playback cannot handle the source tracks. FFmpeg selects the first audio track and encodes stereo AAC. It copies supported H.264 video unless conversion is forced; otherwise it transcodes video to 720p H.264.

The earlier local FFmpeg check produced audible stereo and a clear picture past five minutes on the reported release. A historical 35–45 second stall occurred during conversion. Long-session stability remains a separate check.

Conversion sends sequential fragmented MP4 output. There is no Range-based delivery or conversion restart from a requested source timestamp. **Do not assume arbitrary seeking works**, especially beyond the output generated so far. That needs a different delivery path.

Install both `ffmpeg` and `ffprobe` on the backend host. Browser users need no yt-dlp, codec pack or external player for this workflow. The host supplies conversion CPU and bandwidth. The conversion endpoint accepts the configured TorBox host suffixes.

## CATALOGUE AND SOURCE COVERAGE

Cinemeta supports keyless browsing, search, IMDb-title metadata and seasons. TMDB provides the alternative catalogue, metadata and season data when configured. OMDb ratings, Fanart.tv movie logos and RPDB posters enrich the TMDB metadata path; do not assume that every Cinemeta response gets the same artwork or ratings. TheTVDB currently has a credential test only.

TorBox supplies cache availability, account downloads and playback links. A successful credential test establishes access to that probe, not complete metadata coverage. Poster matching from TorBox release filenames is best-effort.

The discovery desk uses an editorial film selection with mood and tag-overlap suggestions. General movie/TV browsing and search use the live catalogue. AI search and Trakt sync remain planned work.

Seven indexer adapters are available. DMM queries selected, media-compatible sources; EZTV is series-only. Add-on and browser searches do not have identical coverage. In particular, Nyaa, LimeTorrents and TorrentDownloads require a title that the current add-on search path does not supply.

Source filters and sorting apply to the returned set before page display. Source pages initially render 24 matches, with controls to show more. Fetching further upstream results incrementally is separate work.

## INSTANCE DATA AND PRIVATE LINKS

This is a trusted single-instance build. It has no app authentication or per-user isolation, and the default CORS setting is `*`. Visitors to one shared deployment share provider settings and saved records. Use separate databases for separate installations, and keep the backend within your trusted network.

Provider credentials are readable values in MongoDB. Anyone with database access can read them. Browser local storage remembers display preferences such as poster size and theme; it is not the main provider-key store.

The disconnect-and-erase control clears the six main provider configuration fields. It does not erase saved records, backups, old URLs or alternate key overrides stored with add-on installation records. Treat it as disconnecting the main configuration, not comprehensive secure erasure.

New Harbor/Stremio installations use private random identifiers. Their manifest URLs are credential-equivalent links, not public share links. Older installation URLs can contain a reversibly encoded TorBox key. Keep both kinds private and replace old installations if their links have been exposed.

RPDB posters pass through the backend so browser image URLs do not expose the RPDB key. That does not replace instance authentication or protect the database from people who already have access.

## ON THE LIST

Router extraction from `server.py`, Trakt sync, AI search, per-user settings and authentication, more robust conversion delivery, and incremental upstream source fetching remain separate work. These are directions, not release promises.
