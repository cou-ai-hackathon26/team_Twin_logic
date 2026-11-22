/**
 * Microphone recorder that produces a 16 kHz mono 16-bit WAV in the browser.
 *
 * Capturing raw PCM (instead of MediaRecorder's webm/opus) means the backend
 * needs no codec and the speech model gets lossless audio.
 */

const TARGET_SR = 16000

const WORKLET_SRC = `
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (ch) this.port.postMessage(ch.slice(0))
    return true
  }
}
registerProcessor('pcm-capture', PcmCapture)
`

export interface RecorderHandle {
  stop: () => Promise<Blob>
  cancel: () => void
  /** RMS level of the most recent audio, 0..1 */
  level: () => number
  sampleRate: number
}

export async function startRecording(): Promise<RecorderHandle> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('This browser cannot record audio. Use Chrome or Edge on http://localhost.')
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true },
  })
  const ctx = new AudioContext()
  const source = ctx.createMediaStreamSource(stream)
  const analyser = ctx.createAnalyser()
  analyser.fftSize = 1024
  source.connect(analyser)
  const chunks: Float32Array[] = []
  let node: AudioNode

  if (ctx.audioWorklet) {
    const url = URL.createObjectURL(new Blob([WORKLET_SRC], { type: 'application/javascript' }))
    await ctx.audioWorklet.addModule(url)
    URL.revokeObjectURL(url)
    const w = new AudioWorkletNode(ctx, 'pcm-capture')
    w.port.onmessage = (e: MessageEvent<Float32Array>) => chunks.push(e.data)
    node = w
  } else {
    // Fallback for very old browsers
    const sp = ctx.createScriptProcessor(4096, 1, 1)
    sp.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
    node = sp
  }
  source.connect(node)
  // keep the graph running without playing the microphone back
  const mute = ctx.createGain()
  mute.gain.value = 0
  node.connect(mute).connect(ctx.destination)

  const buf = new Float32Array(analyser.fftSize)
  const cleanup = () => {
    stream.getTracks().forEach((t) => t.stop())
    source.disconnect()
    node.disconnect()
    void ctx.close()
  }

  return {
    sampleRate: ctx.sampleRate,
    level: () => {
      analyser.getFloatTimeDomainData(buf)
      let s = 0
      for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i]
      return Math.min(1, Math.sqrt(s / buf.length) * 4)
    },
    cancel: cleanup,
    stop: async () => {
      const sr = ctx.sampleRate
      cleanup()
      const total = chunks.reduce((n, c) => n + c.length, 0)
      const pcm = new Float32Array(total)
      let off = 0
      for (const c of chunks) {
        pcm.set(c, off)
        off += c.length
      }
      return encodeWav(resample(pcm, sr, TARGET_SR), TARGET_SR)
    },
  }
}

/** Windowed-average resampler; good enough for speech at 16 kHz. */
export function resample(x: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return x
  const ratio = from / to
  const n = Math.floor(x.length / ratio)
  const out = new Float32Array(n)
  for (let i = 0; i < n; i++) {
    const start = i * ratio
    const end = Math.min(x.length, start + ratio)
    let s = 0
    let c = 0
    for (let j = Math.floor(start); j < end; j++) {
      s += x[j]
      c++
    }
    out[i] = c ? s / c : 0
  }
  return out
}

export function encodeWav(pcm: Float32Array, sr: number): Blob {
  const buffer = new ArrayBuffer(44 + pcm.length * 2)
  const v = new DataView(buffer)
  const str = (o: number, s: string) => {
    for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i))
  }
  str(0, 'RIFF')
  v.setUint32(4, 36 + pcm.length * 2, true)
  str(8, 'WAVE')
  str(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true) // PCM
  v.setUint16(22, 1, true) // mono
  v.setUint32(24, sr, true)
  v.setUint32(28, sr * 2, true)
  v.setUint16(32, 2, true)
  v.setUint16(34, 16, true)
  str(36, 'data')
  v.setUint32(40, pcm.length * 2, true)
  let o = 44
  for (let i = 0; i < pcm.length; i++, o += 2) {
    const s = Math.max(-1, Math.min(1, pcm[i]))
    v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([buffer], { type: 'audio/wav' })
}
