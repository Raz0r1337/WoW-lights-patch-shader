/* D3D9-Gegenprobe für die gepatchten Vertex-Shader (unter Wine, mingw-Build).
 *
 * Liest cases.bin (von tests/d3d9_check.py erzeugt), legt je Fall den
 * Vertex-Shader an (Prüfung durch die D3D9-Laufzeit), zeichnet die Vertices
 * als 1-Pixel-Punkte und schreibt die gelesene Farbe nach result.bin.
 *
 * cases.bin:  u32 W, H, n
 *   je Fall:  u32 vslen, vs[vslen]; u32 pslen, ps[pslen];
 *             f32 consts[256*4];
 *             u32 nelem; je Element u32 usage, usageIndex;
 *             u32 nvert; f32 verts[nvert*nelem*4]
 * result.bin: je Fall i32 hr_create, i32 hr_draw, u8 rgba[W*H*4]
 */
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned rd32(FILE *f) { unsigned v; fread(&v, 4, 1, f); return v; }

int main(int argc, char **argv)
{
    FILE *in = fopen(argc > 1 ? argv[1] : "cases.bin", "rb");
    FILE *out = fopen(argc > 2 ? argv[2] : "result.bin", "wb");
    if (!in || !out) { printf("Dateien nicht offen\n"); return 1; }
    unsigned W = rd32(in), H = rd32(in), n = rd32(in);

    HWND wnd = CreateWindowA("STATIC", "t", WS_OVERLAPPEDWINDOW, 0, 0, W, H, 0, 0, 0, 0);
    IDirect3D9 *d3d = Direct3DCreate9(D3D_SDK_VERSION);
    D3DPRESENT_PARAMETERS pp = {0};
    pp.Windowed = TRUE; pp.SwapEffect = D3DSWAPEFFECT_DISCARD;
    pp.BackBufferWidth = W; pp.BackBufferHeight = H; pp.BackBufferFormat = D3DFMT_A8R8G8B8;
    pp.hDeviceWindow = wnd;
    IDirect3DDevice9 *dev = NULL;
    HRESULT hr = IDirect3D9_CreateDevice(d3d, 0, D3DDEVTYPE_HAL, wnd,
            D3DCREATE_HARDWARE_VERTEXPROCESSING, &pp, &dev);
    if (FAILED(hr)) { printf("CreateDevice 0x%08lx\n", hr); return 1; }
    D3DCAPS9 caps; IDirect3DDevice9_GetDeviceCaps(dev, &caps);
    printf("VS 0x%08lx, VS-Konstanten %lu\n", caps.VertexShaderVersion, caps.MaxVertexShaderConst);

    IDirect3DSurface9 *rt, *sys;
    IDirect3DDevice9_GetRenderTarget(dev, 0, &rt);
    IDirect3DDevice9_CreateOffscreenPlainSurface(dev, W, H, D3DFMT_A8R8G8B8, D3DPOOL_SYSTEMMEM, &sys, NULL);
    IDirect3DDevice9_SetRenderState(dev, D3DRS_LIGHTING, FALSE);
    IDirect3DDevice9_SetRenderState(dev, D3DRS_FOGENABLE, FALSE);
    IDirect3DDevice9_SetRenderState(dev, D3DRS_ZENABLE, FALSE);
    IDirect3DDevice9_SetRenderState(dev, D3DRS_CULLMODE, D3DCULL_NONE);
    float one = 1.0f;
    IDirect3DDevice9_SetRenderState(dev, D3DRS_POINTSIZE, *(DWORD *)&one);

    for (unsigned c = 0; c < n; c++) {
        unsigned vl = rd32(in); DWORD *vs = malloc(vl); fread(vs, 1, vl, in);
        unsigned pl = rd32(in); DWORD *ps = malloc(pl); fread(ps, 1, pl, in);
        float *k = malloc(256 * 16); fread(k, 16, 256, in);
        unsigned ne = rd32(in);
        D3DVERTEXELEMENT9 el[17];
        for (unsigned e = 0; e < ne; e++) {
            unsigned u = rd32(in), ui = rd32(in);
            D3DVERTEXELEMENT9 x = {0, (WORD)(16 * e), D3DDECLTYPE_FLOAT4, D3DDECLMETHOD_DEFAULT, (BYTE)u, (BYTE)ui};
            el[e] = x;
        }
        D3DVERTEXELEMENT9 end = D3DDECL_END(); el[ne] = end;
        unsigned nv = rd32(in);
        float *v = malloc(nv * ne * 16); fread(v, 16 * ne, nv, in);

        IDirect3DVertexShader9 *vsh = NULL; IDirect3DPixelShader9 *psh = NULL;
        IDirect3DVertexDeclaration9 *decl = NULL;
        int hc = IDirect3DDevice9_CreateVertexShader(dev, vs, &vsh);
        int hd = -1;
        if (SUCCEEDED(hc) && SUCCEEDED(IDirect3DDevice9_CreatePixelShader(dev, ps, &psh))) {
            IDirect3DDevice9_CreateVertexDeclaration(dev, el, &decl);
            IDirect3DDevice9_SetVertexDeclaration(dev, decl);
            IDirect3DDevice9_SetVertexShader(dev, vsh);
            IDirect3DDevice9_SetPixelShader(dev, psh);
            IDirect3DDevice9_SetVertexShaderConstantF(dev, 0, k, 256);
            IDirect3DDevice9_Clear(dev, 0, NULL, D3DCLEAR_TARGET, 0x00000000, 1.0f, 0);
            IDirect3DDevice9_BeginScene(dev);
            hd = IDirect3DDevice9_DrawPrimitiveUP(dev, D3DPT_POINTLIST, nv, v, 16 * ne);
            IDirect3DDevice9_EndScene(dev);
            IDirect3DDevice9_GetRenderTargetData(dev, rt, sys);
        }
        fwrite(&hc, 4, 1, out); fwrite(&hd, 4, 1, out);
        D3DLOCKED_RECT lr;
        unsigned char *row = calloc(W, 4);
        if (hd == 0 && SUCCEEDED(IDirect3DSurface9_LockRect(sys, &lr, NULL, D3DLOCK_READONLY))) {
            for (unsigned y = 0; y < H; y++) fwrite((char *)lr.pBits + y * lr.Pitch, 4, W, out);
            IDirect3DSurface9_UnlockRect(sys);
        } else {
            for (unsigned y = 0; y < H; y++) fwrite(row, 4, W, out);
        }
        free(row);
        if (decl) IDirect3DVertexDeclaration9_Release(decl);
        if (vsh) IDirect3DVertexShader9_Release(vsh);
        if (psh) IDirect3DPixelShader9_Release(psh);
        free(vs); free(ps); free(k); free(v);
    }
    fclose(out);
    printf("%u Fälle\n", n);
    return 0;
}
