# Reshape a scanned part in voxel space, before it is meshed. Called by scan.py for the parts in SHAPES.
#
# block (Marcelo 2026-11-21: 218 g in Cura, mostly walls and supports for detail nobody sees):
#   1. the crankcase gets a plain inside. Its inside (webs, ribs, bores) and the deck on top (the plate
#      with the bores, under the head) are hidden once the head, sump and flywheel are on. Everything closer than REACH to that inside, and more than WALL from the outside
#      (measured across, in each horizontal slice), is removed. The outside is untouched, the inside becomes
#      a smooth wall, and the crankcase is a tube open at the top and bottom that only widens going up: no
#      ceilings, so no supports inside. Parts bolted on the outside (oil filter, water pump) stay solid.
#   2. the alternator is filled solid inside its can (the original's insides were deleted in the hand
#      simplification). Its vents become shallow recesses. The pin stays.
import numpy as np

WALL = 2.0        # mm, the crankcase's new inside wall
GAP_CLOSE = 2.0   # mm, openings in the crankcase walls narrower than 2x this are bridged when finding its inside
REACH = 6.0       # mm, how far from the crankcase's inside material may go: webs and ribs up to 2x this thick
TOP_SPAN = 5.0    # mm, the crankcase's outline this far below the head carries on up through the deck
KEEP_R = 8.0      # mm, material this close to a pulley pin's axis is never hollowed
KEEP_DEPTH = 15.0 # mm, ... for this far behind the pulley


DEBUG = None      # a dict to receive intermediate grids (dev only)
def log(*a): print('SHAPE', *a, flush=True)


def sweep(reach, wall, ax):
    """Grow reach along one axis, both ways, through voxels that are not wall (a whole row at once)."""
    n = reach.shape[ax]; sh = [1] * reach.ndim; sh[ax] = n
    idx = np.arange(n, dtype=np.int16).reshape(sh)
    for flip in (False, True):
        r = np.flip(reach, ax) if flip else reach
        w = np.flip(wall, ax) if flip else wall
        last_wall = np.maximum.accumulate(np.where(w, idx, -1), axis=ax)
        last_reach = np.maximum.accumulate(np.where(r, idx, -1), axis=ax)
        new = (last_reach > last_wall) & ~w
        del last_wall, last_reach
        reach |= np.flip(new, ax) if flip else new
    return reach


def flood(seed, wall, axes):
    """Everything connected to seed without crossing wall, moving along the given axes."""
    reach = seed & ~wall
    while True:
        before = int(reach.sum())
        for ax in axes: reach = sweep(reach, wall, ax)
        if int(reach.sum()) == before: return reach


def shift_or(dst, src, ax, d):
    a = [slice(None)] * 3; b = [slice(None)] * 3
    if d > 0: a[ax] = slice(1, None); b[ax] = slice(None, -1)
    else: a[ax] = slice(None, -1); b[ax] = slice(1, None)
    dst[tuple(a)] |= src[tuple(b)]


def dil2(a, n):
    """Dilate in x and y only (each horizontal slice on its own), n voxels, alternating 4- and 8-neighbour
    steps so the result is round-ish rather than a square or a diamond."""
    a = a.copy()
    for s in range(n):
        b = a.copy()
        for ax in (0, 1):
            for d in (1, -1): shift_or(b, a, ax, d)
        if s % 2:
            for dx in (1, -1):
                t = np.zeros_like(a); shift_or(t, a, 0, dx)
                for dy in (1, -1): shift_or(b, t, 1, dy)
        a = b
    return a


def dil6(a):
    b = a.copy()
    for ax in range(3):
        for d in (1, -1): shift_or(b, a, ax, d)
    return b


def smooth(M):
    """The same 1-2-1 blur scan.py applies before meshing at 0.5."""
    f = M.astype(np.float32)
    for ax in range(3):
        a = [slice(None)] * 3; b = [slice(None)] * 3; a[ax] = slice(1, None); b[ax] = slice(None, -1)
        g = f * 2; g[tuple(a)] += f[tuple(b)]; g[tuple(b)] += f[tuple(a)]; g *= 0.25; f = g
    return f


def box(T):
    p = T.reshape(-1, 3); return p.min(0), p.max(0)


def block(M, org, G, TR, surface):
    shape = M.shape
    X, Y, Z = (org[i] + (np.arange(shape[i]) + 0.5) * G for i in range(3))
    ix = lambda i, v: int(np.clip(np.floor((v - org[i]) / G), 0, shape[i] - 1))
    vox = lambda n: n * G ** 3 / 1000                     # voxel count -> cm3

    # --- 1. the crankcase
    # walls: the block, plus the surface of every other part (they close it when the engine is assembled)
    O = np.zeros(shape, bool)
    for n, T in TR.items():
        if n != 'block': O |= surface(T)
    O = dil6(O)                                            # so their shells are watertight at this voxel size
    # the flywheel's hub hole leads through the rear crank hole into the crankcase: count the flywheel as solid
    flo, fhi = box(TR['flywheel']); assert np.argmin(fhi - flo) == 0, 'flywheel axis expected along x'
    fy, fz, fr = (flo[1] + fhi[1]) / 2, (flo[2] + fhi[2]) / 2, (fhi[1] - flo[1]) / 2
    O[ix(0, flo[0]):ix(0, fhi[0]) + 1] |= (np.hypot(Y[:, None] - fy, Z[None, :] - fz) < fr)[None]
    # the slab between the sump (below) and the head (above)
    k0, k1 = ix(2, box(TR['sump'])[1][2]), ix(2, box(TR['cylinder_head'])[0][2]) + 1
    sl = (slice(None), slice(None), slice(k0, k1))
    wall = M[sl] | O[sl]; del O
    border = np.zeros_like(wall); border[0] = border[-1] = True; border[:, 0] = border[:, -1] = True
    n = max(1, int(round(GAP_CLOSE / G)))
    reach = flood(border, dil2(wall, n), (0, 1)); del border
    cav = ~wall & ~dil2(reach, n); del reach, wall          # enclosed in its slice, small gaps bridged
    # keep only the crankcase: the enclosed space around the crankshaft's axis
    clo, chi = box(TR['crank_pulley']); cy, cz = (clo[1] + chi[1]) / 2, (clo[2] + chi[2]) / 2
    seed = np.zeros_like(cav)
    seed[:, abs(Y - cy) < 1.0, :] = True
    seed &= (abs(Z[k0:k1] - cz) < 1.0)[None, None, :]
    C = flood(seed & cav, ~cav, (0, 1, 2)); del seed, cav
    log('crankcase inside found: %.1f cm3, z %.1f..%.1f mm' % (vox(C.sum()), Z[k0], Z[k1 - 1]))
    if DEBUG is not None: DEBUG.update(C=C.copy(), k0=k0)
    # the deck goes too (Marcelo 2026-11-21: "should be hollow inside the block but it is covered"), so
    # the block is open at the top like a box. Above the slab, the crankcase's outline from its top
    # TOP_SPAN mm (U) carries on up, and the deck's holes inside U (bores, bolt holes) count as inside.
    k2 = shape[2]; kU = max(k0, k1 - int(round(TOP_SPAN / G)))
    U = C[:, :, kU - k0:].any(axis=2)
    top = M[:, :, kU:k2]
    border = np.zeros_like(top); border[0] = border[-1] = True; border[:, 0] = border[:, -1] = True
    holes = ~top & ~dil2(flood(border, dil2(top, n), (0, 1)), n); del border, top
    Cx = np.zeros(shape[:2] + (k2 - k0,), bool); Cx[:, :, :k1 - k0] = C; del C
    Cx[:, :, kU - k0:] |= holes & U[:, :, None]; del holes
    near = Cx.copy(); near[:, :, kU - k0:] |= U[:, :, None]
    sl = (slice(None), slice(None), slice(k0, k2))
    F = M[sl] | Cx
    # what goes: near the inside (within REACH of it) and more than WALL from the outside, in one piece
    # with the crankcase (so it opens at the top and bottom and never leaves a sealed hole)
    E = ~dil2(~F, max(1, int(round(WALL / G)))) & dil2(near, max(1, int(round(REACH / G)))); del near
    H = flood(E & Cx, ~E, (0, 1, 2)); del E, Cx
    # never hollow around the pulley pins
    for p in ('crank_pulley', 'alternator_pulley'):
        plo, phi = box(TR[p]); py, pz = (plo[1] + phi[1]) / 2, (plo[2] + phi[2]) / 2
        near = np.hypot(Y[:, None] - py, Z[None, k0:k2] - pz) < KEEP_R
        H[:ix(0, phi[0] + KEEP_DEPTH)] &= ~near[None]
    # no ceilings inside (printed upright, a ceiling needs supports): going up, the hollow may only stay
    # or widen. Built from the top down: each slice's hollow is cut back to the one above it, plus one
    # voxel every second slice (about 27 degrees from vertical, inside Cura's 35 degree support angle).
    up = np.ones(shape[:2], bool)                          # open above the top
    for k in range(H.shape[2] - 1, -1, -1):
        H[:, :, k] &= dil2(up[:, :, None], 1)[:, :, 0] if k % 2 else up
        up = H[:, :, k] | ~F[:, :, k]                      # empty in the result: hollowed, or never solid
    if DEBUG is not None: DEBUG['H'] = H.copy()
    F &= ~H
    log('crankcase hollowed: removed %.1f cm3, block %.1f -> %.1f cm3' % (
        vox(H.sum()), vox(M.sum()), vox(M.sum() - M[sl].sum() + F.sum())))
    M[sl] = F; del F
    # hollowing must not cut anything off: a piece held on only through the inside (part of the rear plate
    # was) gets the removed material within REACH of it back. Repeated until everything hangs together.
    clo, chi = box(TR['crank_pulley'])
    anchor = np.zeros(shape, bool)                         # the crank pin: never hollowed, part of the block
    anchor[:ix(0, chi[0] + KEEP_DEPTH)] = (np.hypot(Y[:, None] - cy, Z[None, :] - cz) < KEEP_R)[None]
    removed = np.zeros(shape, bool); removed[sl] = H; del H
    for attempt in range(4):
        Mm = smooth(M) >= 0.5                              # what the mesh will keep (thin bridges vanish)
        loose = Mm & ~flood(anchor & Mm, ~Mm, (0, 1, 2)); del Mm
        cut = loose & dil6(removed)                        # loose and touching what was taken away
        if not cut.any(): break
        back = cut
        for _ in range(int(round(REACH / G))): back = dil6(back)
        back &= removed
        M |= back; removed &= ~back
        log('reconnected %d loose voxels: %.1f cm3 put back' % (int(cut.sum()), vox(back.sum())))
    del removed, anchor

    # --- 2. the alternator, solid inside its can
    plo, phi = box(TR['alternator_pulley']); py, pz = (plo[1] + phi[1]) / 2, (plo[2] + phi[2]) / 2
    R = np.hypot(Y[:, None] - py, Z[None, :] - pz)
    th = ((np.arctan2(Z[None, :] - pz, Y[:, None] - py) + np.pi) / (2 * np.pi) * 72).astype(int) % 72
    ring = (R > 3.5) & (R < 30)                            # off the pin, within reach of the can
    inner = {}                                             # x index -> (angles with a wall, median wall radius)
    for i in range(ix(0, phi[0]), shape[0]):
        rr = np.full(72, np.inf); s = M[i] & ring
        np.minimum.at(rr, th[s], R[s])
        f = np.isfinite(rr); inner[i] = (int(f.sum()), float(np.median(rr[f])) if f.any() else 0.0)
    i0 = min(i for i, (na, _) in inner.items() if na >= 66)  # the can: full turns of wall behind the pulley
    i1 = i0
    while i1 + 1 in inner and inner[i1 + 1][0] >= 66: i1 += 1
    r_fill = float(np.median([r for i, (na, r) in inner.items() if i0 <= i <= i1 and r > 8]))
    before = int(M[i0:i1 + 1].sum())
    M[i0:i1 + 1] |= (R < r_fill)[None]
    log('alternator filled: x %.1f..%.1f mm, radius %.1f mm, +%.1f cm3' % (X[i0], X[i1], r_fill, vox(M[i0:i1 + 1].sum() - before)))

    # --- 3. no sealed holes: filling the crankcase closes off small pockets behind its rear wall, which
    # would print as hidden walls inside the solid (and show as an extra shell in the mesh)
    edge = np.zeros(shape, bool); edge[[0, -1]] = True; edge[:, [0, -1]] = True; edge[:, :, [0, -1]] = True
    void = ~M & ~flood(edge, M, (0, 1, 2)); del edge
    M |= void
    log('sealed holes filled: %.2f cm3' % vox(void.sum()))
    return M


SHAPES = {'block': block}
