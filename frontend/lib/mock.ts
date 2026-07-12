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
};

export type MockRace = {
  id: string;
  date: string;
  course: string;
  number: number;
  name: string;
  distance: string;
  entries: MockEntry[];
};

export const MOCK_RACES: MockRace[] = [
  {
    id: "R001",
    date: "2026-07-26",
    course: "モック競馬場",
    number: 11,
    name: "モック記念(G1)",
    distance: "芝2000m",
    entries: [
      {
        horseId: "H001", horseName: "モックスター", horseBirth: "2022-04-08",
        jockeyName: "模擬 太郎", jockeyBirth: "1990-08-08", post: 1,
      },
      {
        horseId: "H002", horseName: "モックウインド", horseBirth: "2021-03-21",
        jockeyName: "模擬 花子", jockeyBirth: "1995-11-02", post: 2,
      },
    ],
  },
];
