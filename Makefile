MADS ?= mads
MADS_FLAGS ?= -f -s

BUILD_DIR := build
MADS_SRC_DIR := $(BUILD_DIR)/.mads-src

# These targets cover the standalone game sources that can be translated
# cleanly to MADS from the material currently present in this repo.

TARGETS := \
	$(BUILD_DIR)/avalanche.xex \
	$(BUILD_DIR)/battle-in-the-b-ring.xex \
	$(BUILD_DIR)/bonk.xex \
	$(BUILD_DIR)/bopotron.xex \
	$(BUILD_DIR)/elevator-repairman.xex \
	$(BUILD_DIR)/fill-er-up.xex \
	$(BUILD_DIR)/fill-er-up-ii.xex \
	$(BUILD_DIR)/harvey.xex \
	$(BUILD_DIR)/livewire.xex \
	$(BUILD_DIR)/planetary-defense.xex \
	$(BUILD_DIR)/race-in-space.xex \
	$(BUILD_DIR)/speedski.xex

.PHONY: all clean

all: $(TARGETS)

define build_game
$(BUILD_DIR)/$(2).xex: $(1) tools/madsify.py
	@mkdir -p "$(BUILD_DIR)" "$(MADS_SRC_DIR)"
	python3 tools/madsify.py "$(3)" "$(MADS_SRC_DIR)/$(2).asm"
	$(MADS) "$(MADS_SRC_DIR)/$(2).asm" $(MADS_FLAGS) -o:"$$@"
endef

$(eval $(call build_game,Avalanche.asm,avalanche,Avalanche.asm))
$(eval $(call build_game,Battle\ In\ The\ B\ Ring.asm,battle-in-the-b-ring,Battle In The B Ring.asm))
$(eval $(call build_game,Bonk.asm,bonk,Bonk.asm))
$(eval $(call build_game,Bopotron.asm,bopotron,Bopotron.asm))
$(eval $(call build_game,Elevator\ Repairman.asm,elevator-repairman,Elevator Repairman.asm))
$(eval $(call build_game,Fill\ Er\ Up.asm,fill-er-up,Fill Er Up.asm))
$(eval $(call build_game,Fill\ Er\ Up\ II.asm,fill-er-up-ii,Fill Er Up II.asm))
$(eval $(call build_game,Harvey.asm,harvey,Harvey.asm))
$(eval $(call build_game,Livewire.asm,livewire,Livewire.asm))
$(eval $(call build_game,Planetary\ Defense.asm,planetary-defense,Planetary Defense.asm))
$(eval $(call build_game,RaceInSpace.asm,race-in-space,RaceInSpace.asm))
$(eval $(call build_game,speedski.asm,speedski,speedski.asm))

clean:
	rm -rf "$(BUILD_DIR)"
