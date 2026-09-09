/* Appended to a generated copy of the pinned mod runtime, on the emulator
 * thread. Use the existing validated package state and persistence code. */
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
