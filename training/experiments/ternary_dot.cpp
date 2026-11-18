// Integer dot products for a scratch BitLinear with one scale per layer.
// In packed storage, one 64-bit word records positive signs and one negative signs.
#include <cstdint>
#if defined(__x86_64__) && (defined(__GNUC__) || defined(__clang__))
#include <immintrin.h>
#define HIVE_X86 1
#else
#define HIVE_X86 0
#endif

extern "C" int hive_has_vnni() {
#if HIVE_X86
    return __builtin_cpu_supports("avx512vnni") && __builtin_cpu_supports("avx512bw") &&
           __builtin_cpu_supports("avx512f");
#else
    return 0;
#endif
}

static void reference(const int8_t *x, const uint64_t *pos, const uint64_t *neg,
                      int32_t *y, int tokens, int rows, int cols) {
    const int stride = (cols + 63) / 64;
    for (int t = 0; t < tokens; ++t) {
        for (int r = 0; r < rows; ++r) {
            int dot = 0;
            for (int k = 0; k < cols; ++k) {
                const int offset = r * stride + k / 64;
                const uint64_t bit = uint64_t(1) << (k % 64);
                const int sign = int(bool(pos[offset] & bit)) - int(bool(neg[offset] & bit));
                dot += sign * int(x[t * cols + k]);
            }
            y[t * rows + r] = dot;
        }
    }
}

#if HIVE_X86
template<bool Packed>
__attribute__((target("avx512f,avx512bw,avx512vnni")))
static void vnni_dot(const int8_t *x, const uint8_t *offset_weights, const uint64_t *pos, const uint64_t *neg,
                     int32_t *y, int tokens, int rows, int cols) {
    const int blocks = (cols + 63) / 64;
    const __m512i one = _mm512_set1_epi8(1);
    for (int t = 0; t < tokens; ++t) {
        const int8_t *input = x + t * cols;
        int correction = 0;
        for (int k = 0; k < cols; ++k) correction += input[k];
        for (int r = 0; r < rows; ++r) {
            __m512i acc = _mm512_setzero_si512();
            for (int b = 0; b < blocks; ++b) {
                const int start = b * 64;
                const int left = cols - start;
                const __mmask64 valid = left >= 64 ? ~uint64_t(0) : (uint64_t(1) << left) - 1;
                const __m512i input_bytes = _mm512_maskz_loadu_epi8(valid, input + start);
                __m512i weights;
                if constexpr (Packed) {
                    const int i = r * blocks + b;
                    weights = _mm512_mask_set1_epi8(one, neg[i], 0);
                    weights = _mm512_mask_set1_epi8(weights, pos[i], 2);
                } else {
                    weights = _mm512_maskz_loadu_epi8(valid, offset_weights + r * cols + start);
                }
                acc = _mm512_dpbusd_epi32(acc, weights, input_bytes);
            }
            // The stored unsigned weights equal the ternary values plus one.
            y[t * rows + r] = _mm512_reduce_add_epi32(acc) - correction;
        }
    }
}
#endif

extern "C" void hive_dot(int mode, const int8_t *x, const uint8_t *offset_weights, const uint64_t *pos,
                         const uint64_t *neg, int32_t *y, int tokens, int rows, int cols) {
#if HIVE_X86
    if (hive_has_vnni() && mode == 1) {
        vnni_dot<false>(x, offset_weights, pos, neg, y, tokens, rows, cols);
        return;
    }
    if (hive_has_vnni() && mode == 2) {
        vnni_dot<true>(x, offset_weights, pos, neg, y, tokens, rows, cols);
        return;
    }
#endif
    reference(x, pos, neg, y, tokens, rows, cols);
}
