# Engenharia de prompts para geração audiovisual

Sumário: 1. Separação de responsabilidades · 2. Princípios universais · 3. Shot-spec e perfis · 4. Continuidade · 5. Integração com o motion programático · 6. Fluxo de decisão

## 1. Separação de responsabilidades
- **Decisão criativa** (o que mostrar, por quê) → `shot-spec` (contrato). Independe da ferramenta.
- **Particularidades da ferramenta** (template, limites de tamanho, o que ela não faz bem) → `prompt-profiles/<ferramenta>.json`.
- **Regras universais de direção** → este documento.
Trocar de ferramenta = trocar o perfil. O roteiro e o shot-spec não mudam. Não misture limitações de uma ferramenta com regras universais.

Não invente capacidades, parâmetros ou comandos de ferramentas externas. Os perfis incluídos (`generic-image`, `generic-video`) são **modelos não verificados** (`capabilities_verified: false`): para uma ferramenta real, copie o modelo, preencha com o que a documentação oficial confirma e só então marque como verificado.

## 2. Princípios universais
Cada prompt descreve, conforme a necessidade: **sujeito · ação · ambiente · composição/enquadramento · movimento de câmera · iluminação · atmosfera/estilo · duração e proporção · restrições**.
- Instruções concretas e visuais; evite pilhas de adjetivos.
- Curto e organizado vence enorme e repetitivo (limite por perfil).
- Não misture instruções incompatíveis (câmera estática + movimento intenso); se quiser mudança, descreva a sequência ("fixa por 2 s, depois push-in lento").
- Texto legível, mãos, física e continuidade são pontos fracos comuns: não dependa deles; componha texto e logo por código.
- Gere assets pensando na composição: fundos limpos, sem primeiro plano, na proporção final.

## 3. Shot-spec e perfis
```bash
python $SK/scripts/prompt_build.py --list
python $SK/scripts/prompt_build.py --shot plano-3.json --profile generic-video
```
Campos obrigatórios do `shot-spec`: `id, subject, action, framing, duration_s, aspect, profile`. A saída é um prompt com `status: generated` (montado, **não enviado**) e avisos: perfil não verificado, excesso de palavras, texto em ferramenta sem suporte confirmado, câmera incompatível, ausência de `continuity_refs`.

## 4. Continuidade
Defina uma "bíblia visual" (personagem, figurino, paleta, lente, hora do dia, textura) e repita as referências em todos os planos (`continuity_refs`); use imagem de referência/seed quando a ferramenta permitir. Combine origens diferentes na composição com grão, vinheta e gradação comuns.

## 5. Integração com o motion programático
Assets de IA entram como camadas (`drawImage` no Canvas, com parallax/grão) ou em FFmpeg. Texto, logo, números e setas continuam sendo código. Registre no relatório quais assets são de IA e quais foram feitos em código. Direitos de uso e rotulagem dependem da ferramenta e do contexto: verifique.

## 6. Fluxo de decisão
`INTENT → PROFILE → MODULES → STYLE ALIAS → ENGINE → SHOT PARAMETERS → FINAL PROMPT/RENDER`
- INTENT: briefing (`creative-brief`).
- PROFILE: perfil de entrega (`profiles/`: formato, fps, zona segura).
- MODULES: módulos que o Core aciona (narrativa, técnicas, áudio…).
- STYLE ALIAS: preset de estilo (`styles/`: paleta, easing, tempo, som, o que evitar).
- ENGINE: motor escolhido (`engines.py select`).
- SHOT PARAMETERS: `shot-spec` quando há IA; marcas de tempo e cenas quando é programático.
- FINAL PROMPT/RENDER: prompt montado (IA) ou vídeo renderizado (código).
Em produção 100% programática, SHOT PARAMETERS vira roteiro com timecodes e FINAL PROMPT vira o render; não force parâmetros de geração de imagem onde não cabem.
