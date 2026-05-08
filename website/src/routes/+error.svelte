<script>
  // Import images and transition utilities
  import braun1 from "$lib/assets/braun.png";
  import braun2 from "$lib/assets/braun2.png";
  import { fade } from "svelte/transition";
  import "../app.css";

  // Reactive state for the image toggle
  let isToggled = $state(false);

  // Background image constant
  const imgBG = "$lib/assets/web-bg.jpg?enhanced&w=9999";
</script>

<!-- Main container with relative positioning for background layering -->
<div class="relative overflow-hidden">
  <main class="relative z-10 flex min-h-dvh items-center justify-center px-6 py-12">
    <div class="max-w-5xl w-full flex flex-col md:flex-row items-center justify-between gap-12">
      
      <!-- Left Content: Text and Navigation -->
      <div class="flex-1 flex flex-col items-center md:items-start text-center md:text-left space-y-8">
        <div class="space-y-4">
          <h2 class="font-serif text-4xl font-bold tracking-tight text-white md:text-6xl lg:text-7xl">
            [404] <span class="text-error">Risk</span> of contamination detected
          </h2>

          <p class="text-xl leading-relaxed text-base-content/80 italic max-w-lg">
            "[seems like you've lost your way friend, but dont you worry this Braun will help you find your way]"
          </p>
        </div>

        <div class="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <a href="/" class="btn btn-primary btn-lg px-8 shadow-xl hover:scale-105 transition-transform">
            Return to Safety
          </a>
          <button
            onclick={() => window.history.back()}
            class="btn btn-outline btn-lg px-8 hover:bg-white/10 transition-all"
          >
            Go back where you came from
          </button>
        </div>
      </div>

      <!-- Right Content: Interactive Character Toggle -->
      <div class="flex flex-col items-center justify-center shrink-0">
        <button 
          onclick={() => isToggled = !isToggled}
          class="hover-animate relative block size-56 md:size-72 lg:size-80 transition-transform active:scale-95 outline-none cursor-pointer"
        >
          {#if isToggled}
            <img 
              in:fade={{ duration: 200 }}
              src={braun2} 
              alt="Braun secondary" 
              class="h-full w-full object-contain drop-shadow-[0_25px_50px_rgba(0,0,0,0.7)]"
            />
          {:else}
            <img 
              in:fade={{ duration: 200 }}
              src={braun1} 
              alt="Braun primary" 
              class="h-full w-full object-contain drop-shadow-[0_25px_50px_rgba(0,0,0,0.7)]"
            />
          {/if}
        </button>
        
        <span class="mt-6 font-mono text-[10px] uppercase tracking-[0.2em] text-white/20 italic">
          # status_normal
        </span>
      </div>

    </div>
  </main>
</div>

<style>
  /* Custom floating and tilting animation */
  .hover-animate {
    animation: hoverRotate 5s ease-in-out infinite;
  }

  @keyframes hoverRotate {
    0%, 100% {
      transform: translateY(0px) rotate(-3deg);
    }
    50% {
      transform: translateY(-20px) rotate(3deg);
    }
  }

  img {
    background: transparent !important;
  }
</style>