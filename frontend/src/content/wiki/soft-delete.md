# Soft Delete do Diário

Quando um diário é retirado de circulação, ele não some do sistema. Ele apenas deixa de aparecer para a operação e vai para a lixeira administrativa.

## O que acontece quando um diário é ocultado

- o sistema registra quem fez isso;
- salva quando isso aconteceu;
- guarda o motivo informado;
- invalida o PDF oficial anterior;
- tira o diário da visão dos níveis operacionais.

## O que acontece quando um diário é restaurado

- o diário volta a aparecer normalmente;
- os campos de ocultação são limpos;
- o histórico continua registrando que houve exclusão e restauração.

## Por que isso existe

Esse modelo evita três problemas graves:

- perda definitiva de informação importante;
- apagamento sem rastro;
- dificuldade para auditoria ou conferência posterior.

## Quem acessa a lixeira

Somente o nível 1.

A lixeira já permite:

- filtrar por obra;
- filtrar por período;
- revisar o motivo da exclusão;
- restaurar o diário quando necessário.
