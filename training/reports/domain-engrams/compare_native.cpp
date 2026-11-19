// Compare two output-projection-only adapters. Since they do not modify the KV cache,
// the final causal token can be recomputed on the identical prefix after a scale change.
#include "llama.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>

static int top(llama_context *ctx, llama_batch &batch, int vocab) {
    if (llama_decode(ctx, batch)) throw std::runtime_error("decode failed");
    auto logits = llama_get_logits_ith(ctx, -1);
    if (!logits) throw std::runtime_error("missing logits");
    return std::max_element(logits, logits + vocab) - logits;
}

static void fill(llama_batch &batch, const std::vector<int> &tokens, size_t first) {
    batch.n_tokens = 0;
    for (size_t pos = first; pos < tokens.size(); ++pos) {
        int i = batch.n_tokens++;
        batch.token[i] = tokens[pos];
        batch.pos[i] = pos;
        batch.n_seq_id[i] = 1;
        batch.seq_id[i][0] = 0;
        batch.logits[i] = pos + 1 == tokens.size();
    }
}

static void write_piece(std::ostream &out, const llama_model *model, int id) {
    char piece[512];
    int n = llama_token_to_piece(model, id, piece, sizeof(piece), 0, true);
    if (n < 0) throw std::runtime_error("token piece too large");
    out << '\t' << id << '\t';
    for (int i = 0; i < n; ++i)
        out << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(static_cast<unsigned char>(piece[i]));
    out << std::dec;
}

int main(int argc, char **argv) {
    if (argc != 7) {
        std::fprintf(stderr, "usage: compare_native model.gguf v1.gguf v2.gguf prompts.bin output.tsv threads\n");
        return 1;
    }
    llama_backend_init();
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    auto model = llama_model_load_from_file(argv[1], mp);
    if (!model) return 2;
    auto v1 = llama_lora_adapter_init(model, argv[2]);
    auto v2 = llama_lora_adapter_init(model, argv[3]);
    if (!v1 || !v2) return 3;
    auto cp = llama_context_default_params();
    cp.n_threads = cp.n_threads_batch = std::stoi(argv[6]);
    cp.n_ctx = 2048; cp.n_batch = cp.n_ubatch = 512;
    cp.embeddings = false;
    cp.attention_type = LLAMA_ATTENTION_TYPE_CAUSAL;
    auto ctx = llama_init_from_model(model, cp);
    if (!ctx) return 4;
    int status = 0;
    auto batch = llama_batch_init(512, 0, 1);
    try {
        const int vocab = llama_n_vocab(model);
        std::ifstream input(argv[4]);
        std::ofstream output(argv[5]);
        if (!input || !output) throw std::runtime_error("cannot open study files");
        std::vector<int> previous;
        std::string line;
        while (std::getline(input, line, '\0')) {
            auto tab = line.find('\t');
            if (tab == std::string::npos) throw std::runtime_error("bad test record");
            std::string name = line.substr(0, tab), text = line.substr(tab + 1);
            std::vector<int> tokens(512);
            int n = llama_tokenize(model, text.data(), text.size(), tokens.data(), tokens.size(), false, true);
            if (n < 1) throw std::runtime_error("invalid test input length");
            tokens.resize(n);
            size_t common = 0;
            while (common < std::min(previous.size(), tokens.size() - 1) && previous[common] == tokens[common]) ++common;
            if (!llama_kv_cache_seq_rm(ctx, 0, common, -1)) throw std::runtime_error("cannot reset prefix");
            llama_lora_adapter_clear(ctx);
            fill(batch, tokens, common);
            int bare = top(ctx, batch, vocab);
            output << name << '\t' << tokens.size();
            write_piece(output, model, bare);
            for (auto edit : {v1, v2}) {
                llama_lora_adapter_clear(ctx);
                if (llama_lora_adapter_set(ctx, edit, 1.0f)) throw std::runtime_error("adapter activation failed");
                if (!llama_kv_cache_seq_rm(ctx, 0, tokens.size() - 1, -1)) throw std::runtime_error("cannot reset final token");
                fill(batch, tokens, tokens.size() - 1);
                write_piece(output, model, top(ctx, batch, vocab));
            }
            output << std::endl;
            previous = std::move(tokens);
        }
    } catch (const std::exception &ex) {
        std::fprintf(stderr, "%s\n", ex.what());
        status = 5;
    }
    llama_batch_free(batch); llama_free(ctx); llama_free_model(model); llama_backend_free();
    return status;
}
