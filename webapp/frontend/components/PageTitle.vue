<template>
    <div>
        <div id="panHeader"></div>
        <h1 id="page-title" class="text-2xl font-bold mx-5 select-none" @click="handleClick">autokmdb</h1>
    </div>
</template>

<script setup lang="ts">
import { add } from 'date-fns';
import { ref } from 'vue';

const clickCount = ref(0);
const kittyMode = ref(false);


const allCats = [
    "FERRIS.gif",
    "FIREFOX.gif",
    "GHOSTPUFFS.gif",
    "KACE.gif",
    "KINAKO.gif",
    "MANEKI.gif",
    "MIDNIGHT.gif",
    "PUMPKINSPICELATTE.gif",
    "SPRINKLES.gif",
    "STRIPES.gif",
    "VALENTIN.gif",
    "xX_vampiregoth91_Xx.gif",
];

const defaultCats = [
    "STRIPES.gif",
    "KINAKO.gif",
    "MANEKI.gif",
    "MIDNIGHT.gif",
    "FIREFOX.gif",
];

function handleClick() {
    clickCount.value++;
    if (clickCount.value > 1 && clickCount.value < 5) {
        document.getElementById("page-title").innerText = "autokmdb (" + (5 - clickCount.value) + ")";
    }
    if (clickCount.value >= 5 && !kittyMode.value) {
        console.log("Kitty mode activated!");
        kittyMode.value = true;
        document.getElementById("page-title").innerText = "autokmdb (cica mód)";

        const addKitty = () => {
            console.log("Adding kitty");
            const cats = defaultCats;

            const panHeader = document.getElementById("panHeader");
            if (!panHeader) return;

            const img = document.createElement("img");
            const randomCat = cats[Math.floor(Math.random() * cats.length)];
            img.src = "/autokmdb/cats/" + randomCat;
            img.className = "kitty";

            const fromLeft = Math.random() < 0.5;
            if (fromLeft) {
                img.style.left = "-10%";
                img.style.animationName = "kitty-walk-left";
                img.classList.add("left");
            } else {
                img.style.right = "-10%";
                img.style.animationName = "kitty-walk-right";
            }

            panHeader.appendChild(img);

            setTimeout(() => {
                panHeader.removeChild(img);
            }, 20000);
        };

        setInterval(() => {
            if (Math.random() < 0.2) {
                addKitty();
            }
        }, 2000);
        addKitty();
    }
}
</script>

<style>
#panHeader {
    position: absolute;
    top: 50px;
    width: 100%;
    height: 50px;
    pointer-events: none;
}

#page-title {
    cursor: pointer;
}

@keyframes kitty-walk-left {
    from {
        left: -10%;
    }

    to {
        left: 110%;
    }
}

@keyframes kitty-walk-right {
    from {
        right: -10%;
    }

    to {
        right: 110%;
    }
}

.kitty {
    position: absolute;
    bottom: 0;
    width: auto;
    height: 80px;
    z-index: 1000;
}

.kitty {
    animation-duration: 20s;
    animation-timing-function: linear;
    animation-iteration-count: 1;
}

.kitty.left {
    transform: scaleX(-1);
}
</style>