package com.ditto.app.data.demo

import android.content.Context
import android.media.MediaMetadataRetriever
import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.ContentItem
import java.io.File

/** Real generated MP4s, five aligned frames, measured DCT hashes. */
class VideoCorpus(private val context: Context) {
    private val hasher = PerceptualHasher(context)
    fun asset(name: String): File {
        val target=File(context.filesDir,"corpus/$name")
        if(!target.exists()) { target.parentFile?.mkdirs(); context.assets.open("corpus/$name").use { input -> target.outputStream().use { input.copyTo(it) } } }
        return target
    }
    fun hashes(file: File): List<String> = MediaMetadataRetriever().use { retriever ->
        retriever.setDataSource(file.absolutePath)
        val duration=(retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: error("Video duration unavailable"))*1000L
        (0..4).map { i ->
            val bitmap=retriever.getFrameAtTime((duration-100000L).coerceAtLeast(0L)*i/4,MediaMetadataRetriever.OPTION_CLOSEST) ?: error("Frame unavailable")
            try { hasher.hashBitmap(bitmap) } finally { bitmap.recycle() }
        }
    }
    fun original(item: ContentItem): ContentItem {
        val file=asset("original_${item.paletteSeed}.mp4")
        return item.copy(kind=com.ditto.app.domain.model.ContentKind.VIDEO,localUri=android.net.Uri.fromFile(file).toString(),perceptualHash=hashes(file).joinToString("|"),sourcePlatform="Generated demo asset")
    }
    fun measured(candidate: CandidateMatch): CandidateMatch {
        val kind=when(candidate.id) { "cand_001"->"crop"; "cand_002"->"caption"; "cand_003"->"unrelated"; "cand_004"->"resize"; "cand_005"->"fake_endorsement"; "cand_007"->"credited"; "cand_008"->"authorized"; "cand_009"->"ambiguous"; else->"watermark" }
        val original=hashes(asset("original_${candidate.paletteSeed}.mp4"))
        val copy=hashes(asset("${candidate.paletteSeed}_${kind}.mp4"))
        val score=original.zip(copy).map { (a,b)->hasher.similarity(a,b) }.average()
        return candidate.copy(hashSimilarity=score,visualSimilarity=score,
            sourceUrl="https://demo.invalid/${candidate.id}",
            transformNote=(if(candidate.id=="cand_005") "SIMULATED fake endorsement with authored altered-speech scripts. Face embeddings, ASR and manipulation detection are unavailable." else candidate.transformNote)+" Measured five aligned video frames; synthetic asset. Similarity does not establish permission.")
    }
}
