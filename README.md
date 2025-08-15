# Liar's Dice - Jogo Multijogador

*Liar’s Dice* é um jogo de dados para dois ou mais jogadores que envolve blefe e percepção de engano. Cada jogador possui cinco dados escondidos sob um copo, e deve-se adivinhar quantos dados de uma face específica estão sob todos os copos combinados. Os 1 (Ases) são curingas e contam para o valor da aposta atual.

## Proposta
Desenvolver um protocolo de camada de aplicação para um jogo de dados multijogador, permitindo que múltiplos clientes se conectem a um servidor central, formem partidas automaticamente e troquem mensagens para jogar em turnos. O protocolo define as interações entre clientes e o servidor, incluindo entrada em partidas, execução de jogadas, contagem de pontos e término da partida.


## Instruções para execução
> Faça download dos arquivos

> Ponha em qualquer pasta com permissão de usuário

> Abra a pasta no terminal (Ex: PowerShell no Windows)

> Digite os comandos a seguir (ou apenas rode os executáveis do servidor e do cliente):

> ```$ python .\server.py```

> ```$ python .\client.py```

> Copie o IP gerado pelo server.py e cole no campo IP que client.py solicitará

> Rode client.py duas vezes para ter 2 jogadores logados (seguindo a mesma lógica citada anteriormente)

> Insira os nicknames e jogue o jogo conforme as regras ^^.

> Bom jogo!

---

> OBS: caso haja erro relacionado às importações das bibliotecas, é possível instalá-las através do argumento pip

> Ex: ```$ pip install json```, e assim por diante enquanto o seu computador não reconhecer as bibliotecas utilizadas.

> Lista de bibliotecas:
```socket``` ```threading``` ```random``` ```time``` ```json``` ```os``` ```datetime``` ```protocol``` ```sys``` ```rich```

---
Trabalho realizado como tarefa final da disciplina.

Disciplina: **Redes de Computadores** - UFPEL
