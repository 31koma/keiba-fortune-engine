// 開発用Mockデータ(backend/providers/mock.py と同一の架空データ)。
// 実レースデータ連携はPhase 4(DataProvider経由)で行う。占術知識は含まない。
export const MOCK_NOTICE = "開発版:表示は全てMockデータです";

export type MockEntry = {
  horseId: string;
  horseName: string;
  horseBirth: string;
  jockeyName: string;
  jockeyBirth: string;
  post: number;
  /** 単勝オッズ(取得時点スナップショット。集合意識の注目度の近似としてのみ使用) */
  winOdds: number | null;
};

export type MockRace = {
  id: string;
  date: string;
  course: string;
  number: number;
  name: string;
  distance: string;
  entries: MockEntry[];
  /** ⭐今日の注目(開発版Mock。正式実装では知識ベースの規則で決定する) */
  featuredHorseId: string;
};

export const MOCK_RACES: MockRace[] = [
  {
    id: "R001",
    date: "2026-07-26",
    course: "モック競馬場",
    number: 11,
    name: "モック記念(G1)",
    distance: "芝2000m",
    featuredHorseId: "H001",
    entries: [
      {
        horseId: "H001", horseName: "モックスター", horseBirth: "2022-04-08",
        jockeyName: "模擬 太郎", jockeyBirth: "1990-08-08", post: 1, winOdds: 2.4,
      },
      {
        horseId: "H002", horseName: "モックウインド", horseBirth: "2021-03-21",
        jockeyName: "模擬 花子", jockeyBirth: "1995-11-02", post: 2, winOdds: 5.8,
      },
    ],
  },
  {
    id: "R002",
    date: "2026-07-26",
    course: "モック競馬場",
    number: 10,
    name: "モックカップ(G3)",
    distance: "芝1600m",
    featuredHorseId: "H004",
    entries: [
      {
        horseId: "H003", horseName: "モックフレイム", horseBirth: "2022-08-15",
        jockeyName: "模擬 花子", jockeyBirth: "1995-11-02", post: 3, winOdds: 12.6,
      },
      {
        horseId: "H004", horseName: "モックムーン", horseBirth: "2021-12-24",
        jockeyName: "模擬 太郎", jockeyBirth: "1990-08-08", post: 5, winOdds: 3.1,
      },
    ],
  },
];
