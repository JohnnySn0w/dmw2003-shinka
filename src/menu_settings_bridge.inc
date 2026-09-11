/* Appended to a generated copy of the pinned mod runtime, on the emulator
 * thread. Use the existing validated package state and persistence code. */
extern "C" void shinka_battle_motion_reset(void);
extern "C" int shinka_motion_get(int option) {
    if (option < 0 || option > 1) return 100;
    auto& manager = PSXRecompV4::state().manager;
    if (!manager.feature_enabled("shinka.evolution-journal", "menu-chart")) return 100;
    auto text = manager.feature_option_value("shinka.evolution-journal", "menu-chart",
        option ? "battle_action_rate" : "battle_idle_rate");
    return text == "2" ? 200 : text == "1.5" ? 150 : text == "1.25" ? 125 : 100;
}

extern "C" int shinka_motion_set(int option, int value) {
    if (option < 0 || option > 1 || (value != 100 && value != 125 && value != 150 && value != 200)) return 0;
    auto& runtime = PSXRecompV4::state();
    auto previous = runtime.manager;
    std::string error;
    bool ok = runtime.manager.set_feature_option("shinka.evolution-journal", "menu-chart",
        option ? "battle_action_rate" : "battle_idle_rate",
        value == 200 ? "2" : value == 150 ? "1.5" : value == 125 ? "1.25" : "1", &error)
        && PSXRecompV4::mod_runtime_commit(runtime.disc_path, &error);
    if (!ok) {
        runtime.manager = std::move(previous);
        std::fprintf(stderr, "Shinka battle motion setting: %s\n", error.c_str());
        return 0;
    }
    shinka_battle_motion_reset();
    return 1;
}

extern "C" void shinka_rates_get(int* battle, int* dv, int* fixed) {
    auto& manager = PSXRecompV4::state().manager;
    auto value = [&](const char* feature, const char* option, int fallback) {
        if (!manager.feature_enabled("shinka.experience", feature)) return fallback;
        auto text = manager.feature_option_value("shinka.experience", feature, option);
        return text.empty() ? fallback : std::atoi(text.c_str());
    };
    *battle = value("battle-exp", "multiplier", 1);
    *dv = value("dv-exp", "multiplier", 1);
    *fixed = value("dv-exp", "fixed_award", 0);
}

extern "C" int shinka_rates_set(int battle, int dv, int fixed) {
    if (battle < 1 || battle > 4 || dv < 1 || dv > 4 || (fixed != 0 && fixed != 10)) return 0;
    auto& runtime = PSXRecompV4::state();
    auto previous = runtime.manager;
    std::string error;
    auto& manager = runtime.manager;
    bool ok = manager.set_feature_enabled("shinka.experience", "battle-exp", true, &error)
        && manager.set_feature_enabled("shinka.experience", "dv-exp", true, &error)
        && manager.set_feature_option("shinka.experience", "battle-exp", "multiplier", std::to_string(battle), &error)
        && manager.set_feature_option("shinka.experience", "dv-exp", "multiplier", std::to_string(dv), &error)
        && manager.set_feature_option("shinka.experience", "dv-exp", "fixed_award", std::to_string(fixed), &error)
        && PSXRecompV4::mod_runtime_commit(runtime.disc_path, &error);
    if (!ok) {
        runtime.manager = std::move(previous);
        std::fprintf(stderr, "Shinka settings: %s\n", error.c_str());
        return 0;
    }
    std::fprintf(stdout, "Shinka settings: EXP %dx, DV %dx, fixed %d\n", battle, dv, fixed);
    return 1;
}

extern "C" int shinka_encounter_rate_get(void) {
    auto& manager = PSXRecompV4::state().manager;
    if (!manager.feature_enabled("shinka.evolution-journal", "menu-chart")) return 100;
    auto text = manager.feature_option_value("shinka.evolution-journal", "menu-chart", "encounter_rate");
    return text.empty() ? 100 : std::atoi(text.c_str());
}

extern "C" int shinka_encounter_rate_set(int rate) {
    if (rate < 0 || rate > 200 || rate % 50) return 0;
    auto& runtime = PSXRecompV4::state();
    auto previous = runtime.manager;
    std::string error;
    bool ok = runtime.manager.set_feature_option("shinka.evolution-journal", "menu-chart",
                  "encounter_rate", std::to_string(rate), &error)
        && PSXRecompV4::mod_runtime_commit(runtime.disc_path, &error);
    if (!ok) {
        runtime.manager = std::move(previous);
        std::fprintf(stderr, "Shinka encounter settings: %s\n", error.c_str());
        return 0;
    }
    std::fprintf(stdout, "Shinka settings: random encounters %d%%\n", rate);
    return 1;
}

/* Live music palette, sampled once per SPU render block.
 * 0 original, 1 DS, 2 sampled, 3 chip. */
extern "C" int shinka_music_palette_get(void) {
    auto& manager = PSXRecompV4::state().manager;
    if (!manager.feature_enabled("shinka.evolution-journal", "menu-chart")) return 0;
    auto text = manager.feature_option_value("shinka.evolution-journal", "menu-chart", "soundtrack");
    return text.size() == 1 && text[0] >= '0' && text[0] <= '3' ? text[0] - '0' : 0;
}

extern "C" int shinka_music_palette_set(int palette) {
    if (palette < 0 || palette > 3) return 0;
    auto& runtime = PSXRecompV4::state();
    auto previous = runtime.manager;
    std::string error;
    bool ok = runtime.manager.set_feature_option("shinka.evolution-journal", "menu-chart",
                  "soundtrack", std::to_string(palette), &error)
        && PSXRecompV4::mod_runtime_commit(runtime.disc_path, &error);
    if (!ok) {
        runtime.manager = std::move(previous);
        std::fprintf(stderr, "Shinka soundtrack preference: %s\n", error.c_str());
        return 0;
    }
    std::fprintf(stdout, "Shinka soundtrack switched: %d\n", palette);
    return 1;
}

extern "C" int shinka_view_get(int option) {
    if (option < 0 || option > 1) return 0;
    auto& manager = PSXRecompV4::state().manager;
    if (!manager.feature_enabled("shinka.evolution-journal", "menu-chart")) return 0;
    auto text = manager.feature_option_value("shinka.evolution-journal", "menu-chart",
        option ? "battle_zoom" : "battle_view");
    return text.size() == 1 && text[0] >= '0' && text[0] <= (option ? '2' : '1') ? text[0] - '0' : 0;
}

extern "C" int shinka_view_set(int option, int value) {
    if (option < 0 || option > 1 || value < 0 || value > (option ? 2 : 1)) return 0;
    auto& runtime = PSXRecompV4::state();
    auto previous = runtime.manager;
    std::string error;
    bool ok = runtime.manager.set_feature_option("shinka.evolution-journal", "menu-chart",
        option ? "battle_zoom" : "battle_view", std::to_string(value), &error)
        && PSXRecompV4::mod_runtime_commit(runtime.disc_path, &error);
    if (!ok) {
        runtime.manager = std::move(previous);
        std::fprintf(stderr, "Shinka battle view: %s\n", error.c_str());
        return 0;
    }
    return 1;
}
