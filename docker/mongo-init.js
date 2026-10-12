try {
  rs.status();
  print("Replica set rs0 is already initialized");
} catch (error) {
  if (error.codeName !== "NotYetInitialized" && error.code !== 94) {
    throw error;
  }
  rs.initiate({ _id: "rs0", members: [{ _id: 0, host: "mongo:27017" }] });
}

let ready = false;
for (let attempt = 0; attempt < 120; attempt += 1) {
  if (db.hello().isWritablePrimary) {
    ready = true;
    break;
  }
  sleep(500);
}
if (!ready) {
  throw new Error("MongoDB replica set did not become primary");
}

const databaseName = process.env.MONGODB_DATABASE || "blog";
const appDatabase = db.getSiblingDB(databaseName);
const appUsername = process.env.MONGO_APP_USERNAME;
if (!appDatabase.getUser(appUsername)) {
  appDatabase.createUser({
    user: appUsername,
    pwd: process.env.MONGO_APP_PASSWORD,
    roles: [{ role: "readWrite", db: databaseName }],
  });
  print("Application database user created");
} else {
  print("Application database user already exists");
}
