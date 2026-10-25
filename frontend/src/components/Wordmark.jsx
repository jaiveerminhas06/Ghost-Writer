import { useEffect, useRef, useState } from 'react'
import { reduceMotion } from '../lib/format'

/* The signature moment: a WebGL "ghost ink" wordmark. The text is drawn to a hidden 2D canvas, used as a texture,
   and a fragment shader moves it with slow fbm noise, lets the edges catch a violet-to-amber sheen, and draws a faint
   displaced copy drifting behind it like a ghost. The pointer stirs the ink.
   Inspired by collidingScopes/liquid-logo (MIT): edge detection + noise flow + metallic sheen, rewritten small for
   text (see frontend/THIRD_PARTY_NOTICES.md). Falls back to a plain <h1> with no WebGL, a failed shader, or (still
   frame) reduced motion. Pauses when off-screen or the tab is hidden. */
const VERT = `attribute vec2 p; varying vec2 uv; void main(){ uv = p*0.5+0.5; gl_Position = vec4(p,0.,1.); }`
const FRAG = `
precision mediump float;
uniform sampler2D tex; uniform float time; uniform vec2 res; uniform vec2 mouse; uniform float stir;
uniform vec3 ink; uniform vec3 lamp; uniform vec3 glow;
varying vec2 uv;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1.,0.)),u.x), mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),u.x), u.y); }
float fbm(vec2 p){ float v=0., a=.5; for(int i=0;i<4;i++){ v+=a*noise(p); p*=2.03; a*=.5; } return v; }
void main(){
  vec2 asp = vec2(res.x/res.y, 1.);
  float d = distance(uv*asp, mouse*asp);
  float push = exp(-d*d*6.) * stir;                                   // the pointer pushes the ink
  vec2 flow = vec2(fbm(uv*vec2(7.,3.) + time*.12), fbm(uv*vec2(7.,3.) - time*.10 + 9.)) - .5;
  vec2 duv = uv + flow * (.005 + push*.035);                          // slow noise flow
  float a = texture2D(tex, duv).a;                                    // the letters
  vec2 guv = uv + flow*.05 + vec2(-.018, .05) * (.7 + .3*sin(time*.4));
  float g = texture2D(tex, guv).a;                                    // the ghost copy behind
  float e = 1.6 / res.y;
  float gx = texture2D(tex, duv+vec2(e/asp.x,0.)).a - texture2D(tex, duv-vec2(e/asp.x,0.)).a;
  float gy = texture2D(tex, duv+vec2(0.,e)).a - texture2D(tex, duv-vec2(0.,e)).a;
  float edge = clamp(length(vec2(gx,gy))*1.4, 0., 1.);                // edge detection
  float band = fbm(uv*vec2(2.6,1.2) + vec2(time*.18, 0.));
  vec3 sheen = mix(lamp, glow, smoothstep(.38, .68, band));           // violet to amber
  vec3 letter = mix(ink, sheen, clamp(edge*.95 + push*.6, 0., 1.));
  float ga = g * .16 * (1. - a);
  float alpha = a + ga;
  vec3 col = (letter*a + sheen*ga) / max(alpha, 1e-4);
  gl_FragColor = vec4(col*alpha, alpha);
}`

// Read a CSS colour variable (#rrggbb) as 0-1 floats for the shader, so the wordmark follows the theme.
function cssColor(name) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  const h = v.replace('#', '')
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16)
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]
}

export default function Wordmark() {
  const canvasRef = useRef(null)
  const [fallback, setFallback] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    const gl = canvas && canvas.getContext('webgl', { premultipliedAlpha: true, antialias: true })
    if (!gl) { setFallback(true); return }
    const compile = (type, src) => {
      const s = gl.createShader(type)
      gl.shaderSource(s, src); gl.compileShader(s)
      return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null
    }
    const vs = compile(gl.VERTEX_SHADER, VERT), fs = compile(gl.FRAGMENT_SHADER, FRAG)
    if (!vs || !fs) { setFallback(true); return }
    const prog = gl.createProgram()
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog); gl.useProgram(prog)
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)   // one full-screen rectangle
    const loc = gl.getAttribLocation(prog, 'p')
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)
    const U = (n) => gl.getUniformLocation(prog, n)
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex)
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true)
    ;['TEXTURE_MIN_FILTER', 'TEXTURE_MAG_FILTER'].forEach((k) => gl.texParameteri(gl.TEXTURE_2D, gl[k], gl.LINEAR))
    ;['TEXTURE_WRAP_S', 'TEXTURE_WRAP_T'].forEach((k) => gl.texParameteri(gl.TEXTURE_2D, gl[k], gl.CLAMP_TO_EDGE))

    let w = 0, h = 0, raf = 0, visible = true
    const t0 = performance.now()
    const mouse = { x: 0.5, y: 0.5, stir: 0, target: 0 }
    const still = reduceMotion()
    const paintTexture = () => {   // draw the words on a hidden canvas and upload it as the texture
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5)     // cap the pixel ratio: this is decoration
      w = Math.round(canvas.clientWidth * dpr); h = Math.round(canvas.clientHeight * dpr)
      if (!w || !h) return
      canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h)
      const off = document.createElement('canvas'); off.width = w; off.height = h
      const c = off.getContext('2d')
      let px = h * 0.78
      c.font = `400 ${px}px Gloock, 'Iowan Old Style', Georgia, serif`
      const tw = c.measureText('Ghost Writer').width
      if (tw > w * 0.94) px *= (w * 0.94) / tw
      c.font = `400 ${px}px Gloock, 'Iowan Old Style', Georgia, serif`
      c.fillStyle = '#fff'; c.textBaseline = 'alphabetic'; c.fillText('Ghost Writer', w * 0.012, h * 0.74)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, off)
    }
    const colors = () => {
      gl.uniform3fv(U('ink'), cssColor('--ink')); gl.uniform3fv(U('lamp'), cssColor('--lamp')); gl.uniform3fv(U('glow'), cssColor('--glow'))
    }
    const frame = (now) => {
      mouse.stir += (mouse.target - mouse.stir) * 0.06            // ease the pointer's push in and out
      gl.uniform1f(U('time'), still ? 4.0 : (now - t0) / 1000)    // reduced motion: one still frame
      gl.uniform2f(U('res'), w, h); gl.uniform2f(U('mouse'), mouse.x, mouse.y); gl.uniform1f(U('stir'), mouse.stir)
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
      if (!still && visible && !document.hidden) raf = requestAnimationFrame(frame)
    }
    const start = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(frame) }

    // wait for the display font so the texture is drawn in Gloock, not the fallback
    const fontReady = document.fonts ? document.fonts.load('400 80px Gloock').catch(() => {}) : Promise.resolve()
    fontReady.then(() => { paintTexture(); colors(); start() })

    const ro = new ResizeObserver(() => { paintTexture(); start() }); ro.observe(canvas)
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) start() }); io.observe(canvas)
    const onVis = () => { if (!document.hidden) start() }
    document.addEventListener('visibilitychange', onVis)
    const onMove = (e) => { const r = canvas.getBoundingClientRect(); mouse.x = (e.clientX - r.left) / r.width; mouse.y = 1 - (e.clientY - r.top) / r.height; mouse.target = 1 }
    const onLeave = () => { mouse.target = 0 }
    canvas.addEventListener('pointermove', onMove); canvas.addEventListener('pointerleave', onLeave)
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onTheme = () => { colors(); start() }
    mq.addEventListener('change', onTheme)
    const mo = new MutationObserver(onTheme); mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); mo.disconnect()
      mq.removeEventListener('change', onTheme); document.removeEventListener('visibilitychange', onVis)
      canvas.removeEventListener('pointermove', onMove); canvas.removeEventListener('pointerleave', onLeave)
    }
  }, [])

  return (
    <div className="wordmark">
      <h1 className={fallback ? 'wm-text' : 'wm-text sr-only'}>Ghost Writer</h1>
      {!fallback && <canvas ref={canvasRef} aria-hidden="true" />}
    </div>
  )
}
