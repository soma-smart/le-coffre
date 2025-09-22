<script setup lang="ts">
import { createVaultApiVaultSetupPost } from '@/client';
import { client } from '@/client/client.gen';

async function setupVault() {
    console.log('Setting up vault...');
    client.setConfig({
        baseUrl: "http://127.0.0.1:8123/",
    });
    const response = await createVaultApiVaultSetupPost({
        body: {
            nb_shares: 3,
            threshold: 5
        },
    });
    console.log(response);
}
</script>

<template>
    <h1>Test page</h1>
    <div>
        <button @click="setupVault">Setup Vault</button>
    </div>
</template>
